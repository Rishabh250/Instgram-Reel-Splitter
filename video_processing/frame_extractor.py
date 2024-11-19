import cv2 as cv
import os
import zipfile
import tempfile

def extract_frames(video_path, base_folder):
    cap = cv.VideoCapture(video_path)
    frames_dir = tempfile.mkdtemp(dir=base_folder)
    frames_list = []
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_path = os.path.join(frames_dir, f"frame{frame_count:04d}.jpg")
        cv.imwrite(frame_path, frame)
        frames_list.append(frame_path)
        frame_count += 1

    cap.release()

    zip_path = os.path.join(base_folder, "frames.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for frame_path in frames_list:
            zipf.write(frame_path, arcname=os.path.basename(frame_path))

    return zip_path 