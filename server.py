from flask import Flask, Response, render_template, send_from_directory, request, redirect, url_for, send_file
from flask_cors import CORS
import os
import json
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import uuid
import subprocess
import threading

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Directory where DASH videos are stored
DASH_VIDEOS_DIR = Path("dashvideos")
CONFIG_FILE = "config.json"

def load_config():
    """Load camera configuration from JSON file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"cameras": []}

def save_config(config):
    """Save camera configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def get_camera_url(camera):
    """Get camera URL with authentication if needed"""
    url = camera['url']
    if camera.get('username') and camera.get('password'):
        parsed = urlparse(url)
        auth = f"{camera['username']}:{camera['password']}"
        return f"{parsed.scheme}://{auth}@{parsed.netloc}{parsed.path}"
    return url

def start_dash_stream(camera):
    """Start DASH streaming for a camera"""
    output_dir = get_dash_output_dir(camera['guid'])
    output_path = output_dir / "manifest.mpd"
    
    cmd = [
        "ffmpeg",
        "-i", camera["url"],
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-b:v", "2M",
        "-maxrate", "2M",
        "-bufsize", "1M",
        "-g", "48",
        "-keyint_min", "48",
        "-c:a", "aac",
        "-b:a", "128k",
        "-f", "dash",
        "-seg_duration", "4",
        "-frag_duration", "4",
        "-window_size", "10",
        "-extra_window_size", "5",
        "-init_seg_name", f"{output_dir}/init.m4s",  # Keep absolute path for file creation
        "-media_seg_name", f"{output_dir}/chunk-$Number%05d$.m4s",  # Keep absolute path for file creation
        "-use_timeline", "1",
        "-use_template", "1",
        "-ldash", "1",
        "-streaming", "1",
        "-remove_at_exit", "0",
        "-write_prft", "1",
        "-target_latency", "3",
        "-ignore_io_errors", "1",
        "-flags", "+global_header",
        str(output_path)
    ]
    print(f"Starting stream for {camera['name']} ({camera['guid']}) -> {output_path}")
    process = subprocess.Popen(cmd)
    return process

def get_dash_output_dir(camera_guid):
    """Get the output directory for DASH files"""
    # Get current date
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path("E:/bala/version1/dashvideos") / date_str / camera_guid
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we need to create a new date folder
    current_time = datetime.now()
    if current_time.hour == 0 and current_time.minute < 5:  # Check if it's just after midnight
        # Create new date folder
        new_date_str = current_time.strftime("%Y-%m-%d")
        new_output_dir = DASH_VIDEOS_DIR / new_date_str / camera_guid
        new_output_dir.mkdir(parents=True, exist_ok=True)
        return new_output_dir
    
    return output_dir

# Store running processes
running_processes = {}

def get_recordings_by_camera():
    """Get recordings organized by camera and date"""
    recordings = {}
    if DASH_VIDEOS_DIR.exists():
        for camera_dir in DASH_VIDEOS_DIR.iterdir():
            if camera_dir.is_dir():
                camera_guid = camera_dir.name
                recordings[camera_guid] = {}
                for date_dir in camera_dir.iterdir():
                    if date_dir.is_dir():
                        date = date_dir.name
                        recordings[camera_guid][date] = []
                        for mpd_file in date_dir.glob('manifest.mpd'):
                            recordings[camera_guid][date].append(mpd_file.name)
    return recordings

def get_camera_name_by_guid(guid):
    """Get camera name from GUID"""
    config = load_config()
    for camera in config['cameras']:
        if camera['guid'] == guid:
            return camera['name']
    return guid

@app.route('/')
def index():
    """Main page with both live and recorded video players"""
    config = load_config()
    recordings = get_recordings_by_camera()
    
    return render_template('index.html', 
                         recordings=recordings,
                         cameras=config['cameras'],
                         get_camera_name=get_camera_name_by_guid)

@app.route('/live/<int:camera_index>')
def live(camera_index):
    """Live MJPEG stream for specific camera"""
    config = load_config()
    if 0 <= camera_index < len(config['cameras']):
        camera = config['cameras'][camera_index]
        return render_template('live.html', 
                             camera=camera,
                             camera_url=get_camera_url(camera))
    return redirect(url_for('index'))

@app.route('/config')
def config_page():
    """Camera configuration page"""
    config = load_config()
    return render_template('config.html', cameras=config['cameras'])

@app.route('/config/save', methods=['POST'])
def save_camera():
    """Save new camera configuration and start streaming"""
    config = load_config()
    new_camera = {
        'name': request.form['name'],
        'guid': f"cam_{str(uuid.uuid4())[:8]}",  # Generate unique GUID
        'url': request.form['url'],
        'username': request.form.get('username', ''),
        'password': request.form.get('password', '')
    }
    config['cameras'].append(new_camera)
    save_config(config)
    
    # Start DASH streaming in a separate thread
    def start_stream():
        process = start_dash_stream(new_camera)
        running_processes[new_camera['guid']] = process
    
    threading.Thread(target=start_stream).start()
    
    return redirect(url_for('config_page'))

@app.route('/config/delete', methods=['POST'])
def delete_camera():
    """Delete camera configuration and stop streaming"""
    config = load_config()
    index = int(request.form['index'])
    if 0 <= index < len(config['cameras']):
        camera = config['cameras'][index]
        # Stop the DASH stream if it's running
        if camera['guid'] in running_processes:
            process = running_processes[camera['guid']]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            del running_processes[camera['guid']]
        config['cameras'].pop(index)
        save_config(config)
    return redirect(url_for('config_page'))

@app.route('/recorded/<camera_guid>/<date>/<path:filename>')
def recorded(camera_guid, date, filename):
    """Serve recorded DASH video"""
    return render_template('recorded.html', 
                         video_path=f"{camera_guid}/{date}/{filename}",
                         camera_name=get_camera_name_by_guid(camera_guid),
                         date=date)

@app.route('/dashvideos/<path:filename>')
def serve_dash(filename):
    """Serve DASH video files"""
    # Handle the full path structure
    parts = filename.split('/')
    if len(parts) >= 3:  # date/camera_guid/filename
        date = parts[0]
        camera_guid = parts[1]
        file = '/'.join(parts[2:])
        
        # Check if this is a snapshot request
        if "_snapshots" in camera_guid:
            # Extract the actual camera GUID by removing _snapshots
            actual_camera_guid = camera_guid.replace("_snapshots", "")
            # Serve from the snapshot directory but don't expose it in the URL
            response = send_from_directory(str(DASH_VIDEOS_DIR / date / camera_guid), file)
        else:
            response = send_from_directory(str(DASH_VIDEOS_DIR / date / camera_guid), file)
        return response
    response = send_from_directory('dashvideos', filename)
    return response

@app.route('/download_mp4/<date>/<camera_guid>')
def download_mp4(date, camera_guid):
    """Convert DASH video to MP4 and provide download"""
    source_dir = DASH_VIDEOS_DIR / date / camera_guid
    output_mp4 = source_dir / f"{camera_guid}_{date}.mp4"
    
    # Check if manifest exists
    manifest_path = source_dir / "manifest.mpd"
    if not manifest_path.exists():
        print(f"Manifest file not found at: {manifest_path}")
        return "Manifest file not found", 404
    
    try:
        # Create a temporary manifest with relative paths
        temp_manifest = source_dir / "temp_manifest.mpd"
        with open(manifest_path, 'r') as f:
            manifest_content = f.read()
        
        # Replace absolute paths with relative paths
        manifest_content = manifest_content.replace(
            f"E:\\bala\\version1\\dashvideos\\{date}\\{camera_guid}/",
            ""
        )
        
        with open(temp_manifest, 'w') as f:
            f.write(manifest_content)
        
        # Use ffmpeg to convert DASH to MP4
        cmd = [
            "ffmpeg",
            "-i", str(temp_manifest),
            "-c", "copy",  # Copy streams without re-encoding
            "-movflags", "+faststart",  # Enable fast start for web playback
            "-y",  # Overwrite output file if it exists
            str(output_mp4)
        ]
        
        print(f"Running ffmpeg command: {' '.join(cmd)}")
        
        # Run the conversion
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up temporary manifest
        try:
            temp_manifest.unlink()
        except Exception as e:
            print(f"Warning: Could not delete temporary manifest: {e}")
        
        if process.returncode != 0:
            print(f"Error converting video: {process.stderr}")
            return f"Error converting video: {process.stderr}", 500
        
        if not output_mp4.exists():
            print(f"Output file was not created at: {output_mp4}")
            return "Error: Output file was not created", 500
            
        print(f"Successfully created MP4 at: {output_mp4}")
        
        # Send the file for download with proper headers
        response = send_file(
            output_mp4,
            as_attachment=True,
            download_name=f"{camera_guid}_{date}.mp4",
            mimetype='video/mp4'
        )
        
        return response
        
    except Exception as e:
        print(f"Error in download_mp4: {str(e)}")
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 