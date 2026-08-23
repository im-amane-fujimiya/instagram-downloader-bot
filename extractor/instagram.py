import yt_dlp, tempfile, os, glob
def download_insta(link):
    tmpdir = tempfile.mkdtemp()
    output = os.path.join(tmpdir, "%(title)s.%(ext)s")
    ydl_opts = {'outtmpl': output, 'format': 'best', 'quiet': True, 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            files = glob.glob(os.path.join(tmpdir, "*"))
            return files, info, tmpdir
    except Exception as e:
        print(f"Extractor Error: {e}")
        return None, None, tmpdir
