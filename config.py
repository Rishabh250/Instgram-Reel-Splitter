import boto3
import os

# MongoDB configuration
MONGO_URI = "mongodb://localhost:27017"

# AWS S3 configuration
S3_BUCKET = "your-s3-bucket-name"
S3_CLIENT = boto3.client("s3", aws_access_key_id="your-access-key", aws_secret_access_key="your-secret-key")

# Base folder for local storage
BASE_FOLDER = os.path.join(os.getcwd(), "video_processing_files")
os.makedirs(BASE_FOLDER, exist_ok=True) 