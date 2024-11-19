from mongoengine import Document, StringField, DateTimeField, ObjectIdField, ValidationError
from bson import ObjectId

class Video(Document):
    """MongoDB model for video metadata."""
    _id = ObjectIdField(required=True, primary_key=True)
    filename = StringField(required=True)
    s3_key = StringField(required=True)
    uploaded_at = DateTimeField(required=True)
    status = StringField(required=True, choices=["pending", "processing", "completed", "failed"])
    frames_zip_key = StringField(null=True)
    clip_key = StringField(null=True)
    meta = {
        'collection': 'videos'
    }

def save_metadata(metadata):
    """
    Save video metadata to MongoDB.
    
    Args:
        metadata (dict): A dictionary containing video metadata.

    Returns:
        Video: The saved Video document.
    """
    try:
        video = Video(**metadata)
        video.save()
        return video
    except ValidationError as e:
        raise ValueError(f"Invalid metadata provided: {e}") from e

def get_video_metadata(video_id):
    """
    Retrieve video metadata from MongoDB.
    
    Args:
        video_id (str): The ObjectId of the video as a string.

    Returns:
        Video: The Video document or None if not found.
    """
    try:
        # Ensure the ID is treated as an ObjectId
        video = Video.objects(_id=ObjectId(video_id)).first()
        return video
    except Exception as e:
        raise ValueError(f"Error retrieving video metadata: {e}") from e
