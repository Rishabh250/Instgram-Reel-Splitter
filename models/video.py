from bson.objectid import ObjectId

def save_metadata(metadata):
    """Save video metadata to MongoDB."""
    return videos_collection.insert_one(metadata).inserted_id

def get_video_metadata(video_id):
    """Retrieve video metadata from MongoDB."""
    return videos_collection.find_one({"_id": ObjectId(video_id)}) 