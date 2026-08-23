from api.telegram import send_video, send_photo
import os

def handle_media_sending(chat_id, files, caption):
    for file in files[:10]: # carousel max 10
        ext = os.path.splitext(file)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.webp']:
            send_photo(chat_id, file, caption)
        else:
            send_video(chat_id, file, caption)
