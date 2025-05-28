import subprocess
import json
from pathlib import Path
from datetime import datetime

def load_config():
    with open("config.json") as f:
        return json.load(f)

def get_dash_output_dir(camera_guid):
    date_str = datetime.now().strftime("%Y-%m-%d")
    # Create the full path with the specific structure
    output_dir = Path("E:/bala/version1/dashvideos") / date_str / camera_guid
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def start_dash_stream(camera):
    output_dir = get_dash_output_dir(camera['guid'])
    output_path = output_dir / "manifest.mpd"
    
    # Create ffmpeg command with basic parameters
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output files without asking
        "-i", camera["url"],
        "-c:v", "copy",  # Copy video stream
        "-f", "dash",
        "-seg_duration", "2",
        "-init_seg_name", f"{output_dir}/init-stream0.m4s",
        "-media_seg_name", f"{output_dir}/chunk-%d.m4s",
        "-use_timeline", "1",
        "-use_template", "1",
        str(output_path)
    ]
    print(f"Starting stream for {camera['name']} ({camera['guid']}) -> {output_path}")
    subprocess.Popen(cmd)

if __name__ == "__main__":
    config = load_config()
    for camera in config["cameras"]:
        start_dash_stream(camera) 