import subprocess
import json
from pathlib import Path
from datetime import datetime

# Store running processes
running_processes = []

# Directory where DASH videos are stored
DASH_VIDEOS_DIR = Path("dashvideos")

def load_config():
    with open("config.json") as f:
        return json.load(f)

def get_dash_output_dir(camera_guid):
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = DASH_VIDEOS_DIR / date_str / camera_guid
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def start_dash_stream(camera):
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
        str(output_path)
    ]
    print(f"Starting stream for {camera['name']} ({camera['guid']}) -> {output_path}")
    process = subprocess.Popen(cmd)
    running_processes.append(process)
    return process

def stop_all_streams():
    for process in running_processes:
        process.terminate()  # Try to terminate gracefully
        try:
            process.wait(timeout=5)  # Wait for 5 seconds
        except subprocess.TimeoutExpired:
            process.kill()  # Force kill if not terminated
    running_processes.clear()
    print("All streams stopped")

if __name__ == "__main__":
    import sys
    import time
    
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        stop_all_streams()
    else:
        config = load_config()
        for camera in config["cameras"]:
            start_dash_stream(camera)
        
        # Keep running until user presses Ctrl+C
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_all_streams()