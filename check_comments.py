import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
page_id = os.getenv("FACEBOOK_PAGE_ID")

res = httpx.get(
    f"https://graph.facebook.com/v21.0/{page_id}/feed",
    params={
        "fields": "id,message,created_time,comments.limit(20){id,message,created_time,from,comments{id,message,from}}",
        "limit": 10,
        "access_token": token,
    }
)
data = res.json().get("data", [])
print(f"Total posts checked: {len(data)}")
unanswered = 0
for post in data:
    post_id = post.get("id")
    comments = post.get("comments", {}).get("data", [])
    for c in comments:
        c_id = c.get("id")
        msg = c.get("message")
        c_time = c.get("created_time")
        replies = c.get("comments", {}).get("data", [])
        page_replied = any(r.get("from", {}).get("id") == page_id for r in replies)
        safe_msg = repr(msg).encode('ascii', 'backslashreplace').decode('ascii')
        print(f"[{'REPLIED' if page_replied else 'UNANSWERED'}] Post: {post_id} | Comment: {c_id} ({c_time}) -> {safe_msg} | Replies: {len(replies)}")
        if not page_replied:
            unanswered += 1

print(f"\nTotal unanswered comments: {unanswered}")
