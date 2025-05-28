# import cv2
# import subprocess
# import os
# import time
# from datetime import datetime

# def capture_and_convert():
#     # Create output directory if it doesn't exist
#     if not os.path.exists('output'):
#         os.makedirs('output')
    
#     # Generate timestamp for unique filename
#     timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#     temp_video = f'output/temp_{timestamp}.mp4'
#     dash_output = f'output/stream_{timestamp}'
    
#     # Open the MJPEG stream
#     cap = cv2.VideoCapture('http://localhost:56000/mjpeg')
    
#     if not cap.isOpened():
#         print("Error: Could not open MJPEG stream")
#         return
    
#     # Get video properties
#     width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#     fps = 30  # Assuming 30 fps, adjust if needed
    
#     # Create video writer
#     fourcc = cv2.VideoWriter_fourcc(*'mp4v')
#     out = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))
    
#     print("Recording started... Press 'q' to stop")
    
#     try:
#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 print("Error: Could not read frame")
#                 break
                
#             out.write(frame)
            
#             # Display the frame (optional)
#             cv2.imshow('Recording', frame)
            
#             if cv2.waitKey(1) & 0xFF == ord('q'):
#                 break
                
#     finally:
#         # Release resources
#         cap.release()
#         out.release()
#         cv2.destroyAllWindows()
    
#     print("Converting to DASH format...")
    
#     # Convert to DASH format using ffmpeg
#     ffmpeg_cmd = [
#         'ffmpeg', '-i', temp_video,
#         '-c:v', 'libx264', '-crf', '22',
#         '-preset', 'medium',
#         '-b:v', '2M',
#         '-maxrate', '2M',
#         '-bufsize', '1M',
#         '-g', '48',
#         '-sc_threshold', '0',
#         '-keyint_min', '48',
#         '-profile:v', 'main',
#         '-level', '3.1',
#         '-c:a', 'aac',
#         '-b:a', '128k',
#         '-ac', '2',
#         '-ar', '48000',
#         '-f', 'dash',
#         '-seg_duration', '4',
#         '-use_timeline', '1',
#         '-use_template', '1',
#         '-init_seg_name', 'init_$RepresentationID$.m4s',
#         '-media_seg_name', 'chunk_$RepresentationID$_$Number%05d$.m4s',
#         f'{dash_output}/manifest.mpd'
#     ]
    
#     subprocess.run(ffmpeg_cmd)
    
#     # Clean up temporary file
#     os.remove(temp_video)
    
#     print(f"DASH conversion complete. Output saved to {dash_output}")
#     return dash_output

# if __name__ == "__main__":
#     capture_and_convert() 