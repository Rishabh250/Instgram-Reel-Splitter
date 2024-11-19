import os
from datetime import datetime
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from mongoengine import connect
from config import S3_BUCKET, S3_CLIENT, BASE_FOLDER, MONGO_URI
from database.models.video import save_metadata, get_video_metadata, update_video_metadata
from video_processing.clip_cutter import cut_clip
from video_processing.downloader import download_reel
from video_processing.frame_extractor import extract_frames
import shutil

app = Flask(__name__)

connect(db='video_processing', host=MONGO_URI)

def generate_presigned_url(s3_key, expiration=3600):
    try:
        return S3_CLIENT.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=expiration
        )
    except Exception as e:
        app.logger.error("Error generating presigned URL: %s", e)
        return None

def clean_up_folder(folder_path):
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(folder_path)

def handle_file_operations(video_id, user_folder, operation_func, *args):
    try:
        video = get_video_metadata(video_id)
        if not video:
            return jsonify({"error": "Video not found"}), 404
        os.makedirs(user_folder, exist_ok=True)
        video_path = os.path.join(user_folder, video["filename"])
        S3_CLIENT.download_file(S3_BUCKET, video["s3_key"], video_path)
        result = operation_func(video_path, user_folder, *args)
        return result
    except Exception as e:
        app.logger.error("Error during file operation: %s", e)
        return jsonify({"error": "Operation failed"}), 500
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        clean_up_folder(user_folder)

@app.route("/upload_video", methods=["POST"])
def upload_video():
    user_id = request.form.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({"error": "No file provided"}), 400

    filename = secure_filename(file.filename)
    user_folder = os.path.join(BASE_FOLDER, user_id)
    os.makedirs(user_folder, exist_ok=True)
    video_path = os.path.join(user_folder, filename)
    file.save(video_path)

    try:
        metadata = {
            "filename": filename,
            "s3_key": "",
            "uploaded_at": datetime.utcnow(),
            "status": "uploaded",
            "user_id": user_id
        }
        video_id = save_metadata(metadata)
        s3_key = f"{user_id}/{video_id}/video/{filename}"
        S3_CLIENT.upload_file(video_path, S3_BUCKET, s3_key)
        update_video_metadata(video_id, {"s3_key": s3_key})
        download_url = generate_presigned_url(s3_key)
        return jsonify({"message": "File uploaded", "video_id": str(video_id), "download_url": download_url}), 200
    except Exception as e:
        app.logger.error("Error uploading video: %s", e)
        return jsonify({"error": "Video upload failed"}), 500
    finally:
        clean_up_folder(user_folder)

@app.route("/download_reel", methods=["POST"])
def handle_download_reel():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    if "url" not in data:
        return jsonify({"error": "Invalid request"}), 400

    try:
        user_folder = os.path.join(BASE_FOLDER, user_id)
        os.makedirs(user_folder, exist_ok=True)
        video_path = download_reel(data["url"], user_folder)
        if not video_path:
            raise ValueError("Reel download failed")

        filename = os.path.basename(video_path)
        metadata = {
            "filename": filename,
            "s3_key": "",
            "uploaded_at": datetime.utcnow(),
            "status": "downloaded",
            "user_id": user_id
        }
        video_id = save_metadata(metadata)
        s3_key = f"{user_id}/{video_id}/video/{filename}"
        S3_CLIENT.upload_file(video_path, S3_BUCKET, s3_key)
        update_video_metadata(video_id, {"s3_key": s3_key})
        download_url = generate_presigned_url(s3_key)
        return jsonify({"message": "Reel downloaded", "video_id": str(video_id), "download_url": download_url}), 200
    except Exception as e:
        app.logger.error("Error downloading reel: %s", e)
        return jsonify({"error": "Reel download failed"}), 500
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

@app.route("/extract_frames/<video_id>", methods=["POST"])
def handle_extract_frames(video_id):
    def extract_frames_operation(video_path, user_folder):
        user_id = get_video_metadata(video_id)["user_id"]
        zip_path = extract_frames(video_path, user_folder)
        s3_key = f"{user_id}/{video_id}/frames/{os.path.basename(zip_path)}"
        S3_CLIENT.upload_file(zip_path, S3_BUCKET, s3_key)
        update_video_metadata(video_id, {"frames_zip_key": s3_key, "status": "frames_extracted"})
        download_url = generate_presigned_url(s3_key)
        return jsonify({"message": "Frames extracted", "frames_s3_key": s3_key, "download_url": download_url}), 200

    user_folder = os.path.join(BASE_FOLDER, video_id)
    return handle_file_operations(video_id, user_folder, extract_frames_operation)

@app.route("/cut_clip/<video_id>", methods=["POST"])
def handle_cut_clip(video_id):
    data = request.json
    if not data or "startTime" not in data or "endTime" not in data:
        return jsonify({"error": "Invalid request"}), 400

    def cut_clip_operation(video_path, user_folder, start_time, end_time):
        user_id = get_video_metadata(video_id)["user_id"]
        clip_path = cut_clip(video_path, start_time, end_time, user_folder)
        s3_key = f"{user_id}/{video_id}/clips/{os.path.basename(clip_path)}"
        S3_CLIENT.upload_file(clip_path, S3_BUCKET, s3_key)
        update_video_metadata(video_id, {"clip_key": s3_key, "status": "clip_cut"})
        download_url = generate_presigned_url(s3_key)
        return jsonify({"message": "Clip cut", "clip_s3_key": s3_key, "download_url": download_url}), 200

    user_folder = os.path.join(BASE_FOLDER, video_id)
    return handle_file_operations(video_id, user_folder, cut_clip_operation, data["startTime"], data["endTime"])

if __name__ == "__main__":
    app.run(debug=True)
