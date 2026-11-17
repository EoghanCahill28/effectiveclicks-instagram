# Effective Clicks — Instagram auto-poster

Posts to @effectiveclicks on Mon, Wed, Fri and Sun at about 7pm (Irish time).

- `queue/` — approved posts waiting to go out. Folder name starts with the date it should post (`2026-11-18_cafes`). Inside: `1.jpg` (plus `2.jpg`, `3.jpg`… for a carousel) and `caption.txt`.
- `posted/` — posts that went out, each with a `posted.txt` holding the time and the Instagram link.
- To post the next due item right now: **Actions → Post to Instagram → Run workflow**.
- To pull a post: delete its folder from `queue/`.
- If a run fails, GitHub emails you and nothing is posted.

Everything in this repository is public. Only put approved Instagram posts in it.
