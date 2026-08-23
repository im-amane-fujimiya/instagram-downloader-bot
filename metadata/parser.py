def build_caption(info):
    title = info.get('title') or info.get('fulltitle') or "Insta Reel"
    uploader = info.get('uploader') or info.get('uploader_id') or "Instagram User"
    like = info.get('like_count', 'N/A')
    comment = info.get('comment_count', 'N/A')

    caption = f"""🔥 **{title}**

👤 **Creator:** {uploader}
❤️ **Likes:** {like} | 💬 **Comments:** {comment}

✨ **Downloaded by @YourBot**
🚀 Bina Watermark Ke - Shan Bhai ka Bot 😎
"""
    return caption
