# Effective Clicks — Instagram auto-poster

Posts to @effectiveclicks on Instagram (via the Instagram Login API, no Facebook Page needed; also to a Facebook Page if the FB_PAGE_ID secret is set) on Mon, Wed, Fri and Sun at about 7pm (Irish time).

- `queue/` — approved posts waiting to go out. Folder name starts with the date it should post (`2026-11-18_cafes`). Inside: `1.jpg` (plus `2.jpg`, `3.jpg`… for a carousel) and `caption.txt`.
- `posted/` — posts that went out, each with a `posted.txt` holding the time and the Instagram link.
- To post the next due item right now: **Actions → Post to Instagram and Facebook → Run workflow**.
- To pull a post: delete its folder from `queue/`.
- If a run fails, GitHub emails you and nothing is posted.

Everything in this repository is public. Only put approved Instagram posts in it.

## Secrets
- `META_TOKEN` (required): long-lived Instagram User access token from the Meta app dashboard → Instagram → API setup with Instagram login → Generate token. Lasts 60 days; the poster refreshes it on each run and fails loudly (GitHub emails you) when fewer than 10 days are left.
- `IG_USER_ID` (optional): leave unset, the poster uses `me`.
- `FB_PAGE_ID` (optional): only if a Facebook Page should get the posts too.
