import subprocess
import sys
import time
import threading
import os
from pathlib import Path

def run_flask_server():
    """Run the Flask server"""
    print("Starting Flask server...")
    server_process = subprocess.Popen([sys.executable, "server.py"])
    return server_process

def run_dash_streams():
    """Run the DASH streams"""
    print("Starting DASH streams...")
    streams_process = subprocess.Popen([sys.executable, "start_dash_streams.py"])
    return streams_process

def cleanup(server_process, streams_process):
    """Clean up processes"""
    print("\nCleaning up processes...")
    
    # Stop DASH streams first
    if streams_process:
        print("Stopping DASH streams...")
        streams_process.terminate()
        try:
            streams_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            streams_process.kill()
    
    # Then stop the Flask server
    if server_process:
        print("Stopping Flask server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()

def main():
    try:
        # Start Flask server
        server_process = run_flask_server()
        
        # Wait a bit for the server to start
        time.sleep(2)
        
        # Start DASH streams
        streams_process = run_dash_streams()
        
        print("\nBoth server and streams are running!")
        print("Press Ctrl+C to stop everything")
        
        # Keep the script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nReceived stop signal...")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        cleanup(server_process, streams_process)
        print("All processes stopped")

if __name__ == "__main__":
    main() 