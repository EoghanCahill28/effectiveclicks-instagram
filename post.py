"""Effective Clicks Instagram auto-poster.

Each run posts the oldest folder in queue/ whose date (the folder name's
YYYY-MM-DD prefix) is today or earlier, then moves it to posted/.

A queue folder holds:
  1.jpg, 2.jpg, ...  one image = single post, several = carousel (in order)
  caption.txt        the caption, hashtags included

Secrets (GitHub → Settings → Secrets and variables → Actions):
  META_TOKEN   long-lived token with instagram_content_publish
  IG_USER_ID   the Instagram professional account's ID
"""
import datetime
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.parse
import urllib.request

IG_API = "https://graph.instagram.com/v24.0"   # Instagram API with Instagram Login (no Facebook Page needed)
FB_API = "https://graph.facebook.com/v24.0"
TOKEN = os.environ.get("META_TOKEN", "").strip()
IG_USER = os.environ.get("IG_USER_ID", "").strip() or "me"
FB_PAGE = os.environ.get("FB_PAGE_ID", "").strip()  # optional: also post to the Facebook Page
if not TOKEN:
    sys.exit("META_TOKEN secret is missing. Add it under "
             "Settings → Secrets and variables → Actions. Nothing was posted.")
REPO = os.environ["GITHUB_REPOSITORY"]
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
ROOT = pathlib.Path(__file__).parent
QUEUE, POSTED = ROOT / "queue", ROOT / "posted"


class MetaError(Exception):
    pass


def call(method, path, token=None, api=None, **params):
    params["access_token"] = token or TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{api or IG_API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise MetaError(f"Meta API error on {path}: {e.read().decode()}")


def wait_ready(container_id):
    for _ in range(30):
        status = call("GET", container_id, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise MetaError(f"Container {container_id} failed: {status}")
        time.sleep(5)
    raise MetaError(f"Container {container_id} not ready after 150s")


def raw_url(path):
    rel = path.relative_to(ROOT).as_posix()
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{urllib.parse.quote(rel)}"


def post_to_facebook(images, caption):
    """Post the same image(s) and caption to the Facebook Page. Returns a link."""
    page_token = call("GET", FB_PAGE, api=FB_API, fields="access_token")["access_token"]
    if len(images) == 1:
        r = call("POST", f"{FB_PAGE}/photos", api=FB_API, token=page_token,
                 url=raw_url(images[0]), caption=caption)
        return f"https://www.facebook.com/{r.get('post_id', r['id'])}"
    params = {"message": caption}
    for i, img in enumerate(images):
        pid = call("POST", f"{FB_PAGE}/photos", api=FB_API, token=page_token,
                   url=raw_url(img), published="false")["id"]
        params[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    r = call("POST", f"{FB_PAGE}/feed", api=FB_API, token=page_token, **params)
    return f"https://www.facebook.com/{r['id']}"


def token_days_left():
    """Refresh the 60-day Instagram token and return how many days it has left."""
    try:
        r = call("GET", "refresh_access_token", api="https://graph.instagram.com",
                 grant_type="ig_refresh_token")
        return int(r.get("expires_in", 0)) // 86400
    except MetaError as e:
        print(f"Token refresh check failed: {e}")
        return None


def main():
    today = datetime.date.today().isoformat()
    due = sorted(d for d in QUEUE.iterdir() if d.is_dir() and d.name[:10] <= today)
    if not due:
        print("Nothing due today.")
        return
    item = due[0]
    images = sorted(item.glob("*.jpg"), key=lambda p: int(p.stem))
    caption = (item / "caption.txt").read_text().strip()
    if not images:
        sys.exit(f"{item.name}: no .jpg images")

    try:
        link = post_to_instagram(images, caption)
    except MetaError as e:
        sys.exit(f"Instagram post failed, nothing posted: {e}")
    print(f"Instagram: {link}")

    fb_note = "Facebook: not set up (no FB_PAGE_ID secret)"
    fb_failed = False
    if FB_PAGE:
        try:
            fb_note = f"Facebook: {post_to_facebook(images, caption)}"
        except MetaError as e:
            fb_failed = True
            fb_note = f"Facebook FAILED (Instagram post is live): {e}"
    print(fb_note)

    subprocess.run(["git", "mv", str(item), str(POSTED / item.name)], check=True)
    (POSTED / item.name / "posted.txt").write_text(
        f"{datetime.datetime.utcnow().isoformat()}Z\nInstagram: {link}\n{fb_note}\n")
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-m", f"Posted {item.name}"], check=True)
    subprocess.run(["git", "push"], check=True)
    days = token_days_left()
    print(f"Token days left: {days}")
    if fb_failed:
        sys.exit(1)  # so GitHub emails about the Facebook failure
    if days is not None and days < 10:
        sys.exit(f"Post went out, but the Instagram token expires in {days} days. "
                 "Generate a new one in the Meta app dashboard and update the META_TOKEN secret.")


def post_to_instagram(images, caption):
    if len(images) == 1:
        c = call("POST", f"{IG_USER}/media", image_url=raw_url(images[0]), caption=caption)["id"]
    else:
        children = []
        for img in images:
            cid = call("POST", f"{IG_USER}/media", image_url=raw_url(img), is_carousel_item="true")["id"]
            wait_ready(cid)
            children.append(cid)
        c = call("POST", f"{IG_USER}/media", media_type="CAROUSEL",
                 children=",".join(children), caption=caption)["id"]
    wait_ready(c)
    media_id = call("POST", f"{IG_USER}/media_publish", creation_id=c)["id"]
    link = call("GET", media_id, fields="permalink").get("permalink", "")
    return link


if __name__ == "__main__":
    main()
