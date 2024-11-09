import os
import io
import subprocess
import zipfile
import tempfile
import cv2 as cv
import instaloader
import imageio_ffmpeg as ffmpeg_exe
import streamlit as st

# Define base directory for storing all files
base_folder = os.path.join(os.getcwd(), "video_processing_files")
os.makedirs(base_folder, exist_ok=True)  # Create the directory if it doesn't exist

# Custom CSS for styling
st.markdown("""
    <style>
    .main-title { font-size: 3rem; color: #2c3e50; font-weight: 700; text-align: center; margin-bottom: 10px; }
    .sub-title { font-size: 1.5rem; color: #34495e; font-weight: 600; margin-top: 40px; text-align: center; }
    .description { font-size: 1rem; color: #7f8c8d; text-align: center; margin-bottom: 30px; }
    .stButton>button { background-color: #3498db; color: white; font-weight: bold; font-size: 16px; padding: 8px 20px; margin-top: 10px; border: none; border-radius: 5px; }
    .stButton>button:hover { background-color: #2980b9; }
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
        
        # Download the reel to the base folder
        loader.download_post(post, target='video_processing_files')
        
        # Locate the downloaded video file
        video_file = next((f for f in os.listdir('video_processing_files') if f.endswith('.mp4')), None)
        
        if video_file:
            video_path = os.path.join(base_folder, video_file)
            if os.path.getsize(video_path) > 0:  # Check for non-empty file
                with open(video_path, "rb") as f:
                    st.download_button(
                        label="Download Video",
                        data=f.read(),
                        file_name="downloaded_video.mp4",
                        mime="video/mp4"
                    )
                    os.remove(video_path)
            else:
                st.error("Downloaded file is empty")
        else:
            st.error("Video download failed")
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Helper function to extract frames as ZIP
def extract_frames(video_path):
    if not video_path or not os.path.exists(video_path):
        st.error("Invalid video path")
        return None

    cap = cv.VideoCapture(video_path)
    frame_count = 0
    frames_dir = tempfile.mkdtemp(dir=base_folder)  # Unique folder for frames
    frames_list = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_path = os.path.join(frames_dir, f"frame{frame_count:04d}.jpg")
        cv.imwrite(frame_path, frame)
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
    st.write("Your extracted frames are ready for download:")
    st.download_button(
        label="Download Frames as ZIP",
        data=zip_buffer,
        file_name="extracted_frames.zip",
        mime="application/zip"
    )

    # Clean up extracted frames
    for frame_path in frames_list:
        os.remove(frame_path)
    os.rmdir(frames_dir)

# Helper function to cut video clip
def cut_clip(video_path, start_time, end_time):
    if not video_path or not os.path.exists(video_path):
        st.error("Invalid video path")
        return None
    if start_time is None or end_time is None:
        st.error("Start and end times required")
        return None

    output_folder = tempfile.mkdtemp(dir=base_folder) 
    output_path = os.path.join(output_folder, "cut_clip.mp4")

    try:
        ffmpeg_path = ffmpeg_exe.get_ffmpeg_exe()
        command = [
            ffmpeg_path,
            '-i', video_path,
            '-ss', str(start_time),
            '-to', str(end_time),
            '-c', 'copy',
            output_path
        ]
        subprocess.run(command, check=True)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            st.success("Clip cut successfully")
            st.write("Your video clip is ready for download:")
            with open(output_path, "rb") as f:
                st.download_button(
                    label="Download Clip",
                    data=f.read(),
                    file_name="cut_clip.mp4",
                    mime="video/mp4"
                )
        else:
            st.error("Clip cutting failed or produced empty output")
    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        # Clean up output folder
        os.remove(output_path)
        os.rmdir(output_folder)

# UI Structure
st.markdown("<h1 class='main-title'>Video Processing App</h1>", unsafe_allow_html=True)
st.markdown("<p class='description'>Download, extract frames, and cut clips from Instagram Reels or local videos.</p>", unsafe_allow_html=True)

# Download Reel Section
st.markdown("<h2 class='sub-title'>Download Instagram Reel</h2>", unsafe_allow_html=True)
st.write("Enter the Instagram Reel URL to download the video directly.")
url = st.text_input("Instagram Reel URL")
if st.button("Download Reel"):
    download_reel(url)

# Shared File Uploader for Extract Frames and Cut Clip
st.markdown("<h2 class='sub-title'>Upload Video for Processing</h2>", unsafe_allow_html=True)
st.write("Upload a video file to extract frames or cut a specific clip.")
uploaded_video = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi"])

if uploaded_video:
    video_path = os.path.join(base_folder, "uploaded_video.mp4")
    with open(video_path, "wb") as f:
        f.write(uploaded_video.read())

    # Extract Frames Section
    if st.button("Extract Frames"):
        extract_frames(video_path)

    # Cut Clip Section
    st.markdown("<h2 class='sub-title'>Cut Clip</h2>", unsafe_allow_html=True)
    st.write("Select start and end times to extract a specific clip from the uploaded video.")

    cap = cv.VideoCapture(video_path)
    video_duration = int(cap.get(cv.CAP_PROP_FRAME_COUNT) / cap.get(cv.CAP_PROP_FPS))
    cap.release()

    st.write(f"Video duration: {video_duration} seconds")
    start_time, end_time = st.slider(
        "Select the time range for the clip",
        0, video_duration, (0, video_duration // 2)
    )

    if st.button("Cut Clip"):
        cut_clip(video_path, start_time, end_time)

    # Clean up uploaded video after processing
    os.remove(video_path)
