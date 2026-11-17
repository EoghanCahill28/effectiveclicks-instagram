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

API = "https://graph.facebook.com/v24.0"
TOKEN = os.environ["META_TOKEN"]
IG_USER = os.environ["IG_USER_ID"]
REPO = os.environ["GITHUB_REPOSITORY"]
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
ROOT = pathlib.Path(__file__).parent
QUEUE, POSTED = ROOT / "queue", ROOT / "posted"


def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        sys.exit(f"Meta API error on {path}: {body}")


def wait_ready(container_id):
    for _ in range(30):
        status = call("GET", container_id, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            sys.exit(f"Container {container_id} failed: {status}")
        time.sleep(5)
    sys.exit(f"Container {container_id} not ready after 150s")


def raw_url(path):
    rel = path.relative_to(ROOT).as_posix()
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{urllib.parse.quote(rel)}"


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
    print(f"Posted {item.name}: {link}")

    subprocess.run(["git", "mv", str(item), str(POSTED / item.name)], check=True)
    (POSTED / item.name / "posted.txt").write_text(f"{datetime.datetime.utcnow().isoformat()}Z\n{link}\n")
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-m", f"Posted {item.name}"], check=True)
    subprocess.run(["git", "push"], check=True)


if __name__ == "__main__":
    main()
