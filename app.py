import io
import os
import subprocess
import tempfile
import zipfile

import cv2
import imageio_ffmpeg as ffmpeg_exe
import instaloader
import streamlit as st

# Custom CSS for styling
st.markdown("""
    <style>
    .main-title {
        font-size: 3rem;
        color: #2c3e50;
        font-weight: 700;
        text-align: center;
        margin-bottom: 10px;
    }
    .sub-title {
        font-size: 1.5rem;
        color: #34495e;
        font-weight: 600;
        margin-top: 40px;
        text-align: center;
    }
    .description {
        font-size: 1rem;
        color: #7f8c8d;
        text-align: center;
        margin-bottom: 30px;
    }
    .stButton>button {
        background-color: #3498db;
        color: white;
        font-weight: bold;
        font-size: 16px;
        padding: 8px 20px;
        margin-top: 10px;
        border: none;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #2980b9;
    }
    </style>
""", unsafe_allow_html=True)

# Helper function to download Instagram reel
def download_reel(url):
    if not url:
        st.error("No URL provided")
        return None

    loader = instaloader.Instaloader()
    try:
        post = instaloader.Post.from_shortcode(loader.context, url.split("/")[-2])
        temp_dir = tempfile.gettempdir()
        loader.download_post(post, target=temp_dir)
        video_file = next((f for f in os.listdir(temp_dir) if f.endswith('.mp4')), None)
        
        if video_file:
            video_path = os.path.join(temp_dir, video_file)
            st.success("Video downloaded successfully")
            with open(video_path, "rb") as f:
                return io.BytesIO(f.read())
        else:
            st.error("Video download failed")
            return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# Helper function to extract frames as ZIP
def extract_frames(video_path):
    if not video_path or not os.path.exists(video_path):
        st.error("Invalid video path")
        return None

    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    frames_list = []
    temp_dir = tempfile.TemporaryDirectory().name
    os.makedirs(temp_dir, exist_ok=True)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_path = os.path.join(temp_dir, f"frame{frame_count:04d}.jpg")
        cv2.imwrite(frame_path, frame)
        frames_list.append(frame_path)
        frame_count += 1

    cap.release()

    # Zip frames in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for frame_path in frames_list:
            zip_file.write(frame_path, arcname=os.path.basename(frame_path))
    zip_buffer.seek(0)
    st.success("Frames extracted and zipped successfully")
    return zip_buffer

# Helper function to cut video clip as ZIP using imageio-ffmpeg
def cut_clip(video_path, start_time, end_time):
    if not video_path or not os.path.exists(video_path):
        st.error("Invalid video path")
        return None
    if start_time is None or end_time is None:
        st.error("Start and end times required")
        return None

    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, f"clip_{start_time}_{end_time}.mp4")

    try:
        # Use imageio-ffmpeg to locate the ffmpeg binary
        ffmpeg_path = ffmpeg_exe.get_ffmpeg_exe()
        
        # Run ffmpeg command using subprocess
        command = [
            ffmpeg_path,
            '-i', video_path,
            '-ss', str(start_time),
            '-to', str(end_time),
            '-c', 'copy',
            output_path
        ]
        subprocess.run(command, check=True)

        st.success("Clip cut successfully")

        # Zip the output clip in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.write(output_path, arcname="clip.mp4")
        zip_buffer.seek(0)
        return zip_buffer
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# UI Structure
st.markdown("<h1 class='main-title'>Video Processing App</h1>", unsafe_allow_html=True)
st.markdown("<p class='description'>Download, extract frames, and cut clips from Instagram Reels or local videos.</p>", unsafe_allow_html=True)

# Download Reel Section
st.markdown("<h2 class='sub-title'>Download Instagram Reel</h2>", unsafe_allow_html=True)
st.write("Enter the Instagram Reel URL to download the video directly.")
url = st.text_input("Instagram Reel URL")
if st.button("Download Reel"):
    video_data = download_reel(url)
    if video_data:
        st.download_button(
            label="Download Video",
            data=video_data,
            file_name="downloaded_video.mp4",
            mime="video/mp4"
        )

# Extract Frames Section
st.markdown("<h2 class='sub-title'>Extract Frames</h2>", unsafe_allow_html=True)
st.write("Upload a video to extract frames and download them as a ZIP file.")
uploaded_video = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi"], key="frame_extraction")

if uploaded_video:
    temp_video_path = os.path.join(tempfile.gettempdir(), uploaded_video.name)
    with open(temp_video_path, "wb") as f:
        f.write(uploaded_video.read())
    
    if st.button("Extract Frames"):
        frames_zip = extract_frames(temp_video_path)
        if frames_zip:
            st.download_button(
                label="Download Frames as ZIP",
                data=frames_zip,
                file_name="extracted_frames.zip",
                mime="application/zip"
            )

# Cut Clip Section
st.markdown("<h2 class='sub-title'>Cut Clip</h2>", unsafe_allow_html=True)
st.write("Upload a video and select start and end times to extract a specific clip.")
uploaded_clip_video = st.file_uploader("Upload a video file for clip cutting", type=["mp4", "mov", "avi"], key="cut_clip")

if uploaded_clip_video:
    clip_video_path = os.path.join(tempfile.gettempdir(), uploaded_clip_video.name)
    with open(clip_video_path, "wb") as f:
        f.write(uploaded_clip_video.read())
    
    cap = cv2.VideoCapture(clip_video_path)
    video_duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS))
    cap.release()

    st.write(f"Video duration: {video_duration} seconds")
    start_time, end_time = st.slider(
        "Select the time range for the clip",
        0, video_duration, (0, video_duration // 2)
    )

    if st.button("Cut Clip"):
        clip_zip = cut_clip(clip_video_path, start_time, end_time)
        if clip_zip:
            st.download_button(
                label="Download Clip as ZIP",
                data=clip_zip,
                file_name="cut_clip.zip",
                mime="application/zip"
            )
