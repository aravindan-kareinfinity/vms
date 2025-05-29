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
import shutil
import re
import requests

app = Flask(__name__)
# Configure CORS to allow all origins
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
    "expose_headers": ["Content-Type", "X-CSRFToken"],
    "supports_credentials": True,
    "max_age": 600
}})

# Add security headers middleware
@app.after_request
def add_security_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
    response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
    response.headers['Cross-Origin-Embedder-Policy'] = 'credentialless'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    return response

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

def get_dash_output_dir(camera_guid):
    """Get the output directory for DASH files"""
    # Get current date
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path("E:/bala/version1/dashvideos") / date_str / camera_guid
    
    # Create directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we need to create a new date folder
    current_time = datetime.now()
    if current_time.hour == 0 and current_time.minute < 5:  # Check if it's just after midnight
        # Create new date folder
        new_date_str = current_time.strftime("%Y-%m-%d")
        new_output_dir = Path("E:/bala/version1/dashvideos") / new_date_str / camera_guid
        new_output_dir.mkdir(parents=True, exist_ok=True)
        return new_output_dir
    
    return output_dir

def start_dash_stream(camera):
    """Start DASH streaming for a camera"""
    output_dir = get_dash_output_dir(camera['guid'])
    output_path = output_dir / "manifest.mpd"
    
    # Add headers for MJPEG stream
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': '*/*',
        'Connection': 'keep-alive',
        'Referer': 'http://192.168.1.19:56000/',
        'Origin': 'http://192.168.1.19:56000'
    }
    
    cmd = [
        "ffmpeg",
        "-headers", f"User-Agent: Mozilla/5.0\r\nAccept: */*\r\nConnection: keep-alive\r\nReferer: http://192.168.1.19:56000/\r\nOrigin: http://192.168.1.19:56000\r\n",
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
        "-init_seg_name", f"{output_dir}/init.m4s",
        "-media_seg_name", f"{output_dir}/chunk-$Number%05d$.m4s",
        "-use_timeline", "1",
        "-use_template", "1",
        "-ldash", "1",
        "-streaming", "1",
        "-remove_at_exit", "0",
        "-write_prft", "1",
        "-target_latency", "3",
        "-ignore_io_errors", "1",
        "-flags", "+global_header",
        "-window_size", "0",
        "-extra_window_size", "0",
        "-dash_segment_type", "mp4",
        "-dash_playlist_type", "event",
        "-index_correction", "0",
        str(output_path)
    ]
    
    print(f"Starting stream for {camera['name']} ({camera['guid']}) -> {output_path}")
    process = subprocess.Popen(cmd)
    return process

# Store running processes
running_processes = {}

def get_recordings_by_camera():
    """Get recordings organized by camera and date, excluding snapshot directories"""
    recordings = {}
    if DASH_VIDEOS_DIR.exists():
        for camera_dir in DASH_VIDEOS_DIR.iterdir():
            if camera_dir.is_dir() and not camera_dir.name.endswith('_snapshots'):
                camera_guid = camera_dir.name
                recordings[camera_guid] = {}
                for date_dir in camera_dir.iterdir():
                    if date_dir.is_dir() and not date_dir.name.endswith('_snapshots'):
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

def modify_mpd_paths(mpd_content):
    """Modify MPD file to use relative paths"""
    # Replace absolute paths with relative paths
    mpd_content = re.sub(
        r'initialization="[^"]*/([^/"]+)"',
        r'initialization="\1"',
        mpd_content
    )
    mpd_content = re.sub(
        r'media="[^"]*/([^/"]+)"',
        r'media="\1"',
        mpd_content
    )
    return mpd_content

@app.route('/recorded/<camera_guid>/<date>/<path:filename>')
def recorded(camera_guid, date, filename):
    """Serve recorded DASH video and create a snapshot of the MPD if requested"""
    base_dir = Path("E:/bala/version1/dashvideos")
    source_dir = base_dir / date / camera_guid
    
    if filename == "manifest.mpd":
        # Create manifestsnapshot.mpd in the same location as manifest.mpd
        source_manifest = source_dir / "manifest.mpd"
        snapshot_manifest = source_dir / "manifestsnapshot.mpd"
        
        # Copy the manifest file if it exists
        if source_manifest.exists():
            try:
                shutil.copy2(source_manifest, snapshot_manifest)
                print(f"Created snapshot at: {snapshot_manifest}")
            except Exception as e:
                print(f"Error creating snapshot: {e}")
        else:
            print(f"Warning: Source manifest not found at {source_manifest}")
    
    return render_template('recorded.html', 
                         video_path=f"{camera_guid}/{date}/{filename}",
                         camera_name=get_camera_name_by_guid(camera_guid),
                         date=date)

@app.route('/download_mp4/<date>/<camera_guid>')
def download_mp4(date, camera_guid):
    """Convert DASH video to MP4 and provide download"""
    base_dir = Path("E:/bala/version1/dashvideos")
    source_dir = base_dir / date / camera_guid
    output_mp4 = source_dir / f"{camera_guid}_{date}.mp4"
    
    # Check if manifest exists
    manifest_path = source_dir / "manifest.mpd"
    if not manifest_path.exists():
        return "Manifest file not found", 404
    
    try:
        # Use ffmpeg to convert DASH to MP4
        cmd = [
            "ffmpeg",
            "-i", str(manifest_path),
            "-c", "copy",  # Copy streams without re-encoding
            "-movflags", "+faststart",  # Enable fast start for web playback
            str(output_mp4)
        ]
        
        # Run the conversion
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            print(f"Error converting video: {process.stderr}")
            return "Error converting video", 500
        
        # Send the file for download
        return send_file(
            output_mp4,
            as_attachment=True,
            download_name=f"{camera_guid}_{date}.mp4",
            mimetype='video/mp4'
        )
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/create_snapshot/<camera_guid>/<date>')
def create_snapshot(camera_guid, date):
    """Create a snapshot of the current recording"""
    base_dir = Path("E:/bala/version1/dashvideos")
    source_dir = base_dir / date / camera_guid
    snapshot_dir = base_dir / date / f"{camera_guid}_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a unique snapshot ID
    snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = snapshot_dir / f"manifest_{snapshot_id}.mpd"
    
    # Copy the current MPD file and all associated segments
    if (source_dir / "manifest.mpd").exists():
        # Copy the MPD file
        shutil.copy2(source_dir / "manifest.mpd", snapshot_path)
        
        # Copy all segment files
        for segment in source_dir.glob("*.m4s"):
            shutil.copy2(segment, snapshot_dir / segment.name)
    
    # Redirect back to the original recording
    return redirect(url_for('recorded', camera_guid=camera_guid, date=date, filename="manifest.mpd"))

@app.route('/dashvideos/<path:filename>')
def serve_dash(filename):
    """Serve DASH video files"""
    # Handle the full path structure
    parts = filename.split('/')
    if len(parts) >= 3:  # date/camera_guid/filename
        date = parts[0]
        camera_guid = parts[1]
        file = '/'.join(parts[2:])
        base_dir = Path("E:/bala/version1/dashvideos")
        
        # Check if this is a snapshot request
        if "_snapshots" in camera_guid:
            # Extract the actual camera GUID by removing _snapshots
            actual_camera_guid = camera_guid.replace("_snapshots", "")
            # Serve from the snapshot directory but don't expose it in the URL
            response = send_from_directory(str(base_dir / date / camera_guid), file)
        else:
            response = send_from_directory(str(base_dir / date / camera_guid), file)
            
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        return response
    response = send_from_directory('dashvideos', filename)
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET')
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 