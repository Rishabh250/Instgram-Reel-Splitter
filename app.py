import os
from datetime import datetime

from flask import Flask, request, jsonify, send_file
from pymongo import MongoClient
from werkzeug.utils import secure_filename

from config import S3_BUCKET, S3_CLIENT, BASE_FOLDER, MONGO_URI
from models.video import save_metadata, get_video_metadata
from video_processing.clip_cutter import cut_clip
from video_processing.downloader import download_reel
from video_processing.frame_extractor import extract_frames

# Initialize Flask app
app = Flask(__name__)

# MongoDB Setup
client = MongoClient(MONGO_URI)
db = client.video_processing
videos_collection = db.videos

# Upload video route
@app.route("/upload_video", methods=["POST"])
def upload_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    video_path = os.path.join(BASE_FOLDER, filename)
    file.save(video_path)

    # Upload to S3
    s3_key = f"videos/{filename}"
    S3_CLIENT.upload_file(video_path, S3_BUCKET, s3_key)

    # Save metadata to MongoDB
    metadata = {
        "filename": filename,
        "s3_key": s3_key,
        "uploaded_at": datetime.utcnow(),
        "status": "uploaded"
    }
    video_id = save_metadata(metadata)
    os.remove(video_path)
    return jsonify({"message": "File uploaded successfully", "video_id": str(video_id)}), 200

# Download Instagram reel route
@app.route("/download_reel", methods=["POST"])
def handle_download_reel():
    data = request.json
    if not data or "url" not in data:
        return jsonify({"error": "Invalid request"}), 400

    url = data["url"]
    video_path = download_reel(url, BASE_FOLDER)
    if video_path:
        filename = os.path.basename(video_path)
        s3_key = f"reels/{filename}"
        S3_CLIENT.upload_file(video_path, S3_BUCKET, s3_key)

        # Save metadata to MongoDB
        metadata = {
            "filename": filename,
            "s3_key": s3_key,
            "uploaded_at": datetime.utcnow(),
            "status": "downloaded"
        }
        video_id = save_metadata(metadata)
        os.remove(video_path)
        return jsonify({"message": "Reel downloaded successfully", "video_id": str(video_id)}), 200
    else:
        return jsonify({"error": "Failed to download reel"}), 500

# Extract frames route
@app.route("/extract_frames/<video_id>", methods=["POST"])
def handle_extract_frames(video_id):
    video = get_video_metadata(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    video_path = f"{BASE_FOLDER}/{video['filename']}"
    S3_CLIENT.download_file(S3_BUCKET, video["s3_key"], video_path)

    zip_path = extract_frames(video_path, BASE_FOLDER)
    s3_key = f"frames/{os.path.basename(zip_path)}"
    S3_CLIENT.upload_file(zip_path, S3_BUCKET, s3_key)
    os.remove(zip_path)

    # Update MongoDB
    videos_collection.update_one(
        {"_id": video_id},
        {"$set": {"frames_zip_key": s3_key, "status": "frames_extracted"}}
    )
    return jsonify({"message": "Frames extracted successfully", "frames_s3_key": s3_key}), 200

# Cut clip route
@app.route("/cut_clip/<video_id>", methods=["POST"])
def handle_cut_clip(video_id):
    data = request.json
    if not data or "start_time" not in data or "end_time" not in data:
        return jsonify({"error": "Invalid request"}), 400

    video = get_video_metadata(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    video_path = f"{BASE_FOLDER}/{video['filename']}"
    S3_CLIENT.download_file(S3_BUCKET, video["s3_key"], video_path)

    start_time = data["start_time"]
    end_time = data["end_time"]
    clip_path = cut_clip(video_path, start_time, end_time, BASE_FOLDER)
    s3_key = f"clips/{os.path.basename(clip_path)}"
    S3_CLIENT.upload_file(clip_path, S3_BUCKET, s3_key)
    os.remove(clip_path)

    # Update MongoDB
    videos_collection.update_one(
        {"_id": video_id},
        {"$set": {"clip_key": s3_key, "status": "clip_cut"}}
    )
    return jsonify({"message": "Clip cut successfully", "clip_s3_key": s3_key}), 200

if __name__ == "__main__":
    app.run(debug=True)
