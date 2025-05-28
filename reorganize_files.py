import os
from pathlib import Path
import shutil
from datetime import datetime
import json

def load_config():
    """Load camera configuration from JSON file"""
    if os.path.exists("config.json"):
        with open("config.json", 'r') as f:
            return json.load(f)
    return {"cameras": []}

def ensure_directory_structure(date, camera_guid):
    """Ensure the directory structure exists for a specific date and camera"""
    dashvideos_dir = Path("dashvideos")
    date_dir = dashvideos_dir / date
    camera_dir = date_dir / camera_guid
    date_dir.mkdir(parents=True, exist_ok=True)
    camera_dir.mkdir(parents=True, exist_ok=True)
    return camera_dir

def reorganize_files():
    """Reorganize existing DASH files into proper date/camera structure"""
    dashvideos_dir = Path("dashvideos")
    if not dashvideos_dir.exists():
        print("dashvideos directory not found")
        return

    # Get current date in YYYY-MM-DD format
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Load camera configurations
    config = load_config()
    
    # For each camera, create its directory and move files
    for camera in config['cameras']:
        camera_guid = camera['guid']
        target_dir = ensure_directory_structure(current_date, camera_guid)
        
        # Move all DASH files to the target directory
        for file in dashvideos_dir.glob("*"):
            if file.is_file() and file.suffix in ['.mpd', '.m4s']:
                try:
                    shutil.move(str(file), str(target_dir / file.name))
                    print(f"Moved {file.name} to {target_dir}")
                except Exception as e:
                    print(f"Error moving file {file}: {e}")

if __name__ == "__main__":
    reorganize_files() 