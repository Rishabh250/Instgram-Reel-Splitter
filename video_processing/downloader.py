import instaloader
import os

def download_reel(url, base_folder):
    loader = instaloader.Instaloader()
    try:
        post = instaloader.Post.from_shortcode(loader.context, url.split("/")[-2])
        loader.download_post(post, target=base_folder)
        video_file = next((f for f in os.listdir(base_folder) if f.endswith('.mp4')), None)
        return os.path.join(base_folder, video_file) if video_file else None
    except Exception as e:
        print(f"Error downloading reel: {e}")
        return None 