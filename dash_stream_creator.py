import os
import subprocess
import time
import logging
from pathlib import Path

class DASHStreamCreator:
    def __init__(self, mjpeg_url, output_dir="dashvideos"):
        self.mjpeg_url = mjpeg_url
        self.output_dir = Path(output_dir).absolute()
        self.process = None
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("DASHStreamCreator")
        
        # Create output directory structure
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.logger.info(f"All output will be in: {self.output_dir}")

    def create_dash_stream(self):
        """Create DASH-compliant segmented video using FFmpeg with exact segment timeline pattern"""
        cmd = [
            'ffmpeg',
            '-i', self.mjpeg_url,
            '-c:v', 'libx264',  # Use H.264 codec
            '-preset', 'medium',
            '-crf', '22',
            '-b:v', '2M',
            '-maxrate', '2M',
            '-bufsize', '1M',
            '-g', '48',
            '-sc_threshold', '0',
            '-keyint_min', '48',
            '-profile:v', 'main',
            '-level', '3.1',
            '-f', 'dash',
            '-use_template', '1',
            '-use_timeline', '1',
            '-init_seg_name', 'init.m4s',
            '-media_seg_name', 'chunk-$Number%05d$.m4s',
            '-remove_at_exit', '0',  # Keep segments after stopping
            '-window_size', '10',  # Number of segments to keep in manifest
            '-extra_window_size', '5',  # Extra segments to keep
            '-ldash', '1',  # Enable low latency DASH
            '-write_prft', '1',  # Write producer reference time
            '-target_latency', '4',  # Target latency in seconds
            # Custom segment durations to match the pattern
            '-seg_duration', '0.477001',  # First segment
            '-seg_duration', '0.480001',  # Second segment
            '-seg_duration', '0.480002',  # Third segment
            '-seg_duration', '0.480001',  # Fourth segment
            '-seg_duration', '0.480002',  # Fifth segment
            '-seg_duration', '0.480001',  # Sixth segment
            '-seg_duration', '0.054000',  # Final segment
            'manifest.mpd'
        ]

        self.logger.info("Starting DASH stream creation with command:")
        self.logger.info(" ".join(cmd))

        try:
            # Change working directory to ensure all temp files stay in output_dir
            original_cwd = Path.cwd()
            os.chdir(self.output_dir)
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            for line in iter(self.process.stdout.readline, ''):
                if "frame=" in line:
                    self.logger.info(f"Processing: {line.strip()}")
                elif "error" in line.lower():
                    self.logger.error(line.strip())
            
        except KeyboardInterrupt:
            self.logger.info("Stopping stream creation...")
        except Exception as e:
            self.logger.error(f"Error: {str(e)}")
        finally:
            self.cleanup()
            self.verify_output()
            os.chdir(original_cwd)

    def cleanup(self):
        """Clean up the FFmpeg process"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.logger.info("FFmpeg process terminated")

    def verify_output(self):
        """Verify all files are in the correct location"""
        expected_files = {
            'manifest.mpd': "DASH Manifest",
            'init.m4s': "Init Segment",
        }
        
        self.logger.info("\nVerifying file locations:")
        all_valid = True
        
        for filename, desc in expected_files.items():
            filepath = self.output_dir / filename
            if filepath.exists():
                self.logger.info(f"✓ {desc.ljust(15)} at {filepath}")
            else:
                self.logger.error(f"✗ {desc.ljust(15)} MISSING")
                all_valid = False

        segments = list(self.output_dir.glob('chunk-*.m4s'))
        if segments:
            self.logger.info(f"\nFound {len(segments)} media segments in {self.output_dir}:")
            for seg in sorted(segments)[:3]:
                self.logger.info(f"• {seg.name}")
        else:
            self.logger.error("\nNo media segments found in target directory!")
            all_valid = False

        if all_valid:
            self.logger.info("\n✓ All files are in the correct location")
        else:
            self.logger.error("\n✗ Some files are missing or misplaced")

if __name__ == "__main__":
    mjpeg_url = "http://localhost:56000/mjpeg"
    
    creator = DASHStreamCreator(
        mjpeg_url=mjpeg_url,
        output_dir="dashvideos"  # All files will be strictly contained here
    )
    
    try:
        creator.create_dash_stream()
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}") 