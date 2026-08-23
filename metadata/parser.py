def build_caption(info):
    title = info.get('title') or "Insta Reel"
    uploader = info.get('uploader') or "Instagram"

    caption = f"""🔥 **{title}**

👤 **Creator:** {uploader}

✨ **Via Bot - HD Download** 🚀
"""
    return caption
