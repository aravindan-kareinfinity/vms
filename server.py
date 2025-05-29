from flask import Flask, Response, render_template, send_from_directory, request, redirect, url_for
import os
import json
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import uuid

app = Flask(__name__)

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
    """Save new camera configuration"""
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
    return redirect(url_for('config_page'))

@app.route('/config/delete', methods=['POST'])
def delete_camera():
    """Delete camera configuration"""
    config = load_config()
    index = int(request.form['index'])
    if 0 <= index < len(config['cameras']):
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
        base_dir = Path("E:/bala/version1/dashvideos")
        return send_from_directory(str(base_dir / date / camera_guid), file)
    return send_from_directory('dashvideos', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 