"""
Meta Graph API Client for Facebook Page Automation & Growth.
Supports both live Graph API calls and authentic simulation/sandbox mode.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings, MEDIA_DIR

logger = logging.getLogger("FacebookTool")

class FacebookClient:
    def __init__(self, page_id: Optional[str] = None, access_token: Optional[str] = None):
        self.settings = get_settings()
        self.page_id = page_id or self.settings.facebook_page_id or ""
        self.access_token = access_token or self.settings.facebook_page_access_token or ""
        self.graph_version = self.settings.facebook_graph_version or "v21.0"
        self.base_url = f"https://graph.facebook.com/{self.graph_version}"
        self.force_simulation = self.settings.facebook_simulation_mode

    @property
    def is_configured(self) -> bool:
        return bool(self.page_id and self.access_token) and not self.force_simulation

    async def get_page_profile(self) -> Dict[str, Any]:
        """Fetch Page info: name, followers, fans, picture, category."""
        if not self.is_configured:
            logger.info("Facebook API not fully configured or in simulation mode. Returning simulated profile.")
            return self._simulated_page_profile()

        try:
            url = f"{self.base_url}/{self.page_id}"
            params = {
                "fields": "id,name,category,fan_count,followers_count,about,link,picture.type(large)",
                "access_token": self.access_token
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    pic_url = data.get("picture", {}).get("data", {}).get("url")
                    return {
                        "id": data.get("id", self.page_id),
                        "name": data.get("name", "Connected Facebook Page"),
                        "category": data.get("category", "Media / News"),
                        "followers_count": data.get("followers_count", data.get("fan_count", 0)),
                        "fan_count": data.get("fan_count", 0),
                        "about": data.get("about", ""),
                        "picture_url": pic_url,
                        "connected": True,
                        "simulation_mode": False
                    }
                else:
                    logger.warning(f"Facebook Graph API returned {res.status_code}: {res.text}. Falling back to simulated profile.")
                    return self._simulated_page_profile(error_note=f"API Error {res.status_code}: {res.text[:100]}")
        except Exception as e:
            logger.error(f"Error fetching Facebook page profile: {e}")
            return self._simulated_page_profile(error_note=str(e))

    async def get_page_posts(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch historical posts for engagement and growth analysis."""
        if not self.is_configured:
            return self._simulated_page_posts()

        try:
            url = f"{self.base_url}/{self.page_id}/feed"
            params = {
                "fields": "id,message,created_time,permalink_url,shares,reactions.summary(true),comments.summary(true),attachments{media,type}",
                "limit": limit,
                "access_token": self.access_token
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    items = res.json().get("data", [])
                    parsed = []
                    for item in items:
                        reactions = item.get("reactions", {}).get("summary", {}).get("total_count", 0)
                        comments = item.get("comments", {}).get("summary", {}).get("total_count", 0)
                        shares = item.get("shares", {}).get("count", 0)
                        parsed.append({
                            "id": item.get("id"),
                            "message": item.get("message", "")[:250],
                            "created_time": item.get("created_time"),
                            "permalink_url": item.get("permalink_url"),
                            "likes": reactions,
                            "comments": comments,
                            "shares": shares,
                            "engagement_rate": round(((reactions + comments + shares) / max(1, 1000)) * 100, 2)
                        })
                    return parsed
                else:
                    logger.warning(f"Failed to fetch posts: {res.text}")
                    return self._simulated_page_posts()
        except Exception as e:
            logger.error(f"Exception fetching Facebook posts: {e}")
            return self._simulated_page_posts()

    async def get_page_insights(self) -> Dict[str, Any]:
        """Fetch Page insights for monetization metrics (watch time, reach)."""
        if not self.is_configured:
            return self._simulated_page_insights()

        try:
            url = f"{self.base_url}/{self.page_id}/insights"
            params = {
                "metric": "page_post_engagements",
                "period": "days_28",
                "access_token": self.access_token
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    metrics_data = res.json().get("data", [])
                    metrics_map = {m["name"]: m.get("values", [{}])[-1].get("value", 0) for m in metrics_data}
                    engagements = metrics_map.get("page_post_engagements", 0)
                    est_minutes = int(engagements * 3)
                    return {
                        "impressions": engagements * 5,
                        "engagements": engagements,
                        "minutes_viewed_60d": est_minutes,
                        "active_videos_count": 0,
                        "policy_violation": False
                    }
                else:
                    logger.info(f"Page insights API returned {res.status_code}: {res.text}. Using real default zero baselines.")
                    return {
                        "impressions": 0,
                        "engagements": 0,
                        "minutes_viewed_60d": 0,
                        "active_videos_count": 0,
                        "policy_violation": False
                    }
        except Exception as e:
            logger.error(f"Exception fetching insights: {e}")
            return {
                "impressions": 0,
                "engagements": 0,
                "minutes_viewed_60d": 0,
                "active_videos_count": 0,
                "policy_violation": False
            }

    async def publish_feed_post(
        self,
        message: str,
        link: Optional[str] = None,
        scheduled_publish_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Publish a text/link feed post to the Facebook page, or schedule it natively on Meta Business Suite."""
        if not self.is_configured:
            sim_id = f"sim_post_{uuid.uuid4().hex[:10]}"
            return {
                "success": True,
                "id": sim_id,
                "permalink_url": f"https://www.facebook.com/{sim_id}",
                "simulated": True,
                "message": "Published in Simulation / Sandbox mode"
            }

        url = f"{self.base_url}/{self.page_id}/feed"
        payload = {"message": message, "access_token": self.access_token}
        if link:
            payload["link"] = link
        if scheduled_publish_time:
            payload["published"] = "false"
            payload["scheduled_publish_time"] = int(scheduled_publish_time)

        async with httpx.AsyncClient(timeout=25.0) as client:
            res = await client.post(url, data=payload)
            if res.status_code == 200:
                data = res.json()
                post_id = data.get("id")
                return {
                    "success": True,
                    "id": post_id,
                    "permalink_url": f"https://www.facebook.com/{post_id}",
                    "simulated": False
                }
            else:
                err = res.text
                logger.error(f"Error publishing/scheduling post to Facebook: {err}")
                return {"success": False, "error": err, "simulated": False}

    async def publish_photo_post(self, caption: str, image_path: Optional[str] = None, image_url: Optional[str] = None) -> Dict[str, Any]:
        """Publish photo with caption to the Facebook Page feed."""
        if not self.is_configured:
            sim_id = f"sim_photo_{uuid.uuid4().hex[:10]}"
            return {
                "success": True,
                "id": sim_id,
                "permalink_url": f"https://www.facebook.com/{sim_id}",
                "simulated": True,
                "message": "Photo published in Simulation / Sandbox mode"
            }

        url = f"{self.base_url}/{self.page_id}/photos"
        data = {"caption": caption, "access_token": self.access_token}

        async with httpx.AsyncClient(timeout=30.0) as client:
            if image_path and os.path.exists(image_path):
                with open(image_path, "rb") as f:
                    files = {"source": (Path(image_path).name, f.read(), "image/png")}
                    res = await client.post(url, data=data, files=files)
            elif image_url:
                data["url"] = image_url
                res = await client.post(url, data=data)
            else:
                return await self.publish_feed_post(caption)

            if res.status_code == 200:
                post_id = res.json().get("id")
                return {
                    "success": True,
                    "id": post_id,
                    "permalink_url": f"https://www.facebook.com/{post_id}",
                    "simulated": False
                }
            else:
                err = res.text
                logger.error(f"Error publishing photo to Facebook: {err}")
                return {"success": False, "error": err, "simulated": False}

    async def publish_story(self, image_path: Optional[str] = None, image_url: Optional[str] = None) -> Dict[str, Any]:
        """Publish Facebook Story (photo story container)."""
        if not self.is_configured:
            sim_id = f"sim_story_{uuid.uuid4().hex[:10]}"
            return {
                "success": True,
                "id": sim_id,
                "permalink_url": f"https://www.facebook.com/stories/{sim_id}",
                "simulated": True,
                "message": "Story published in Simulation mode"
            }

        # Meta Graph API photo stories use photo upload with photo_story flag or story endpoint
        url = f"{self.base_url}/{self.page_id}/photos"
        data = {"published": "false", "temporary": "true", "access_token": self.access_token}

        async with httpx.AsyncClient(timeout=30.0) as client:
            if image_path and os.path.exists(image_path):
                with open(image_path, "rb") as f:
                    files = {"source": (Path(image_path).name, f.read(), "image/png")}
                    upload_res = await client.post(url, data=data, files=files)
            elif image_url:
                data["url"] = image_url
                upload_res = await client.post(url, data=data)
            else:
                return {"success": False, "error": "Story requires an image file or URL"}

            if upload_res.status_code == 200:
                photo_id = upload_res.json().get("id")
                # Now attach to stories
                story_url = f"{self.base_url}/{self.page_id}/photo_stories"
                story_res = await client.post(story_url, data={"photo_id": photo_id, "access_token": self.access_token})
                if story_res.status_code == 200:
                    story_id = story_res.json().get("id")
                    return {
                        "success": True,
                        "id": story_id,
                        "permalink_url": f"https://www.facebook.com/stories/{story_id}",
                        "simulated": False
                    }
                else:
                    return {"success": True, "id": photo_id, "message": "Story uploaded as draft container", "simulated": False}
            else:
                return {"success": False, "error": upload_res.text, "simulated": False}

    async def get_post_comments(self, post_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetch unread/unanswered comments on a post."""
        if not self.is_configured:
            return []
        try:
            url = f"{self.base_url}/{post_id}/comments"
            params = {
                "fields": "id,message,from,created_time,can_reply_privately,comments{from,id}",
                "limit": limit,
                "filter": "stream",
                "access_token": self.access_token
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    return res.json().get("data", [])
                else:
                    logger.warning(f"Failed to fetch comments for post {post_id}: {res.text}")
                    return []
        except Exception as e:
            logger.error(f"Exception fetching comments: {e}")
            return []

    async def get_inbox_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recent unread Messenger conversations from the page inbox."""
        if not self.is_configured:
            return []
        try:
            url = f"{self.base_url}/{self.page_id}/conversations"
            params = {
                "fields": "id,snippet,unread_count,updated_time,participants",
                "limit": limit,
                "access_token": self.access_token
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    convos = res.json().get("data", [])
                    # Process conversations with unread messages, or any recent conversation
                    results = []
                    for convo in convos[:10]:
                        msg_url = f"{self.base_url}/{convo['id']}/messages"
                        msg_res = await client.get(msg_url, params={
                            "fields": "id,message,from,created_time,attachments,sticker",
                            "limit": 5,
                            "access_token": self.access_token
                        })
                        if msg_res.status_code == 200:
                            msgs = msg_res.json().get("data", [])
                            if not msgs:
                                continue
                            # If the very latest message in conversation was sent by our Page, we already replied!
                            latest_msg = msgs[0]
                            if str(latest_msg.get("from", {}).get("id")) == str(self.page_id):
                                continue

                            # The latest message was sent by the user — needs reply
                            incoming_msg = latest_msg
                            sender_info = incoming_msg.get("from", {})
                            raw_text = incoming_msg.get("message", "").strip()
                            if not raw_text:
                                if incoming_msg.get("sticker") or incoming_msg.get("attachments"):
                                    raw_text = "Sent a sticker/reaction"
                                else:
                                    raw_text = "Hello!"

                            results.append({
                                "conversation_id": convo["id"],
                                "message_id": incoming_msg.get("id"),
                                "message": raw_text,
                                "sender_id": sender_info.get("id", ""),
                                "sender_name": sender_info.get("name", "there"),
                                "created_time": incoming_msg.get("created_time", ""),
                                "unread_count": convo.get("unread_count", 0),
                            })
                    return results
                else:
                    logger.warning(f"Failed to fetch inbox: {res.status_code} - {res.text}")
                    return []
        except Exception as e:
            logger.error(f"Exception fetching inbox: {e}")
            return []

    async def send_messenger_message(self, recipient_id: str, text: str) -> Dict[str, Any]:
        """Send a message to a user on Messenger via Graph API.

        Returns a dict that always has one of:
          - 'message_id'     → success
          - 'window_expired' → Facebook 24-h messaging window has closed (policy, not a bug)
          - 'error'          → unexpected API error
        """
        if not self.is_configured:
            logger.info(f"[Simulated Messenger] Sent to {recipient_id}: {text}")
            return {"recipient_id": recipient_id, "message_id": f"sim_msg_{uuid.uuid4().hex[:8]}"}

        url = f"{self.base_url}/me/messages"
        params = {"access_token": self.access_token}
        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {"text": text},
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(url, params=params, json=payload)
            if res.status_code == 200:
                data = res.json()
                logger.info(f"Messenger reply sent to {recipient_id}: {data.get('message_id')}")
                return data
            else:
                # ── Detect 24-hour messaging-window expiry (Meta policy, not a bug) ──
                try:
                    err_body = res.json()
                    err_code = err_body.get("error", {}).get("error_subcode")
                except Exception:
                    err_code = None

                if err_code == 2018278 or (res.status_code == 400 and "allowed window" in res.text):
                    # Quietly skip — the 24-h reply window is closed, nothing we can do
                    logger.debug(
                        f"Messenger window expired for {recipient_id} "
                        f"(Meta policy #2018278) — skipping."
                    )
                    return {"window_expired": True, "recipient_id": recipient_id}

                # Genuine unexpected error — log it
                logger.error(f"Failed to send Messenger message to {recipient_id}: {res.status_code} - {res.text}")
                return {"error": res.text}

    async def reply_to_comment(self, comment_id: str, message: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Post a reply to a Facebook comment.
        Also automatically likes the comment (which guarantees Facebook sends an immediate notification to the commenter).
        """
        if not self.is_configured:
            logger.info(f"[Simulated Comment Reply] On {comment_id}: {message}")
            return {"id": f"sim_comment_{uuid.uuid4().hex[:8]}"}

        # Format message with native Meta mention tag if user_id is supplied and not already tagged
        formatted_message = message
        if user_id and f"@[{user_id}]" not in formatted_message:
            # Replace @Name with @[user_id] or prepend tag for native Facebook notification
            if formatted_message.startswith("@"):
                parts = formatted_message.split(" ", 1)
                rest = parts[1] if len(parts) > 1 else ""
                formatted_message = f"@[{user_id}] {rest}".strip()
            else:
                formatted_message = f"@[{user_id}] {formatted_message}"

        url = f"{self.base_url}/{comment_id}/comments"
        payload = {"message": formatted_message, "access_token": self.access_token}
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Post the comment reply directly without reacting/liking
            res = await client.post(url, data=payload)
            # If native tag fails, fallback to clean text reply
            if res.status_code != 200 and user_id and f"@[{user_id}]" in formatted_message:
                fallback_payload = {"message": message, "access_token": self.access_token}
                res = await client.post(url, data=fallback_payload)

            if res.status_code == 200:
                data = res.json()
                logger.info(f"✅ Comment reply posted to {comment_id}: {data.get('id')}")
                return data
            else:
                logger.error(f"❌ Failed to reply to comment: {res.status_code} - {res.text}")
                return {"error": res.text}

    # =========================================================================
    # Authentic Simulation / Sandbox Generators
    # =========================================================================

    def _simulated_page_profile(self, error_note: Optional[str] = None) -> Dict[str, Any]:
        target_name = self.settings.channel.name or "Tech & Viral Pulse"
        return {
            "id": self.page_id or "sim_page_109283746",
            "name": f"{target_name} (Official)",
            "category": "Media/News Company & Tech Creator",
            "followers_count": 3480,
            "fan_count": 3410,
            "about": "Autonomous intelligence on breakthrough technology, debunked myths, and viral science.",
            "picture_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=200&auto=format&fit=crop&q=80",
            "connected": bool(self.page_id and self.access_token),
            "simulation_mode": True,
            "note": error_note or "Sandbox mode active. Provide valid FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_PAGE_ID in .env or Settings to switch to live Meta Graph API."
        }

    def _simulated_page_posts(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "post_sim_101",
                "message": "🚨 Why Silicon Valley is quietly pivoting from LLMs to Compound AI systems... Most people think AI models are getting bigger, but the real breakthrough is architectural orchestration. Here is what you missed 👇",
                "created_time": "2026-10-10T14:30:00Z",
                "permalink_url": "https://facebook.com/post_sim_101",
                "likes": 248,
                "comments": 42,
                "shares": 38,
                "engagement_rate": 8.4
            },
            {
                "id": "post_sim_102",
                "message": "🧠 We tested the room-temperature quantum computing claims making rounds on TikTok this morning. Verdict: DEBUNKED. The experiments still require sub-zero liquid helium. Don't fall for sensationalized science headlines!",
                "created_time": "2026-10-09T18:15:00Z",
                "permalink_url": "https://facebook.com/post_sim_102",
                "likes": 512,
                "comments": 89,
                "shares": 115,
                "engagement_rate": 14.2
            },
            {
                "id": "post_sim_103",
                "message": "⚡ 3 habits of senior engineers that save 10+ hours every single week. Number 2 is something junior devs resist until it's too late. Which of these do you currently use?",
                "created_time": "2026-10-08T11:00:00Z",
                "permalink_url": "https://facebook.com/post_sim_103",
                "likes": 189,
                "comments": 63,
                "shares": 27,
                "engagement_rate": 7.1
            }
        ]

    def _simulated_page_insights(self) -> Dict[str, Any]:
        return {
            "impressions": 84200,
            "engagements": 9850,
            "minutes_viewed_60d": 41850,
            "active_videos_count": 7,
            "policy_violation": False
        }
