import os, shutil, glob
def cleanup_temp(path):
    try:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        # temp ke extra files bhi saaf
        for f in glob.glob("/tmp/*video*"):
            try: os.remove(f)
            except: pass
    except Exception as e:
        print(f"Cleanup error: {e}")
