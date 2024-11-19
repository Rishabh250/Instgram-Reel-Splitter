import os
import subprocess
import imageio_ffmpeg as ffmpeg

def cut_clip(video_path, start_time, end_time, base_folder):
    output_path = os.path.join(base_folder, "cut_clip.mp4")
    try:
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        command = [
            ffmpeg_path,
            '-i', video_path,
            '-ss', str(start_time),
            '-to', str(end_time),
            '-c', 'copy',
            output_path
        ]
        subprocess.run(command, check=True)
        return output_path
    except Exception as e:
        print(f"Error cutting clip: {e}")
        return None 