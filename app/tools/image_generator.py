"""
AI Image Generator for Facebook Feed Posts and Stories.
Supports Pollinations (high-fidelity FLUX/SDXL, no key needed), OpenAI DALL-E, Gemini,
with offline graphical poster fallback.
"""
from __future__ import annotations

import logging
import os
import urllib.parse
import uuid
from pathlib import Path
from typing import Optional

import httpx

from app.config import MEDIA_DIR, get_settings

logger = logging.getLogger("ImageGenerator")

class MediaGenerator:
    def __init__(self):
        self.settings = get_settings()
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    async def generate_post_image(self, prompt: str, title: Optional[str] = None, provider: Optional[str] = None) -> str:
        """
        Generate a 1:1 or 4:5 visual for Facebook Feed Posts and Quizzes.
        If provider is 'openai' / 'chatgpt', forces OpenAI DALL-E/gpt-image with fallback.
        """
        active_provider = (provider or self.settings.image_generation_provider).lower()
        if active_provider in ("openai", "chatgpt") and self.settings.openai_api_key:
            res = await self._generate_openai(
                prompt=prompt,
                size="1024x1024",
                prefix="fb_post",
                fallback_title=title or prompt[:60]
            )
            if res:
                return res

        # High-definition Nano Banana / Flux engine (photorealistic Japanese & cinematic scenes)
        return await self._generate_pollinations(
            prompt=prompt,
            width=1080,
            height=1080,
            prefix="fb_post",
            fallback_title=title or prompt[:60],
            model="flux"
        )

    async def generate_story_image(self, prompt: str, overlay_text: Optional[str] = None, provider: Optional[str] = None) -> str:
        """
        Generate a 9:16 vertical visual for Facebook Stories (1080x1920 / 1024x1792).
        """
        active_provider = (provider or self.settings.image_generation_provider).lower()
        if active_provider in ("openai", "chatgpt") and self.settings.openai_api_key:
            res = await self._generate_openai(
                prompt=prompt,
                size="1024x1792",
                prefix="fb_story",
                fallback_title=overlay_text or prompt[:60]
            )
            if res:
                return res

        return await self._generate_pollinations(
            prompt=prompt,
            width=1080,
            height=1920,
            prefix="fb_story",
            fallback_title=overlay_text or prompt[:60],
            model="flux"
        )

    async def _generate_openai(
        self,
        prompt: str,
        size: str,
        prefix: str,
        fallback_title: str
    ) -> Optional[str]:
        """Generate high-fidelity image via OpenAI Images API (DALL-E 3)."""
        file_id = uuid.uuid4().hex[:12]
        filename = f"{prefix}_{file_id}.png"
        target_path = MEDIA_DIR / filename

        enhanced_prompt = (
            f"Hyper-detailed, ultra-clear cinematic photography or modern 3D infographic, "
            f"vibrant aesthetic, studio lighting, award-winning social media visual: {prompt}"
        )

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            model_name = getattr(self.settings, "openai_image_model", "dall-e-3")
            
            logger.info(f"Generating image via OpenAI ({model_name}, {size}): {prompt[:80]}...")
            gen_kwargs = {
                "model": model_name,
                "prompt": enhanced_prompt[:1000],
                "size": size,
                "n": 1
            }
            if "gpt-image" in model_name:
                gen_kwargs["quality"] = "auto"
            else:
                gen_kwargs["quality"] = "standard"

            response = await client.images.generate(**gen_kwargs)
            image_url = response.data[0].url
            if image_url:
                async with httpx.AsyncClient(timeout=45.0) as http_client:
                    img_resp = await http_client.get(image_url)
                    if img_resp.status_code == 200 and len(img_resp.content) > 1024:
                        with open(target_path, "wb") as f:
                            f.write(img_resp.content)
                        logger.info(f"Successfully saved OpenAI media image: {target_path}")
                        return str(target_path)
        except Exception as e:
            logger.warning(f"OpenAI image generation encountered an error: {e}. Falling back to secondary generator.")
        return None

    async def _generate_pollinations(
        self,
        prompt: str,
        width: int,
        height: int,
        prefix: str,
        fallback_title: str,
        model: str = "flux"
    ) -> str:
        """Download high-fidelity image from Nano / Flux / Pollinations or fallback gracefully."""
        file_id = uuid.uuid4().hex[:12]
        filename = f"{prefix}_{file_id}.jpg"
        target_path = MEDIA_DIR / filename

        # Enhance prompt for high viral engagement Facebook aesthetic
        enhanced_prompt = (
            f"Hyper-detailed, ultra-clear cinematic photography or modern 3D infographic, "
            f"vibrant aesthetic, studio lighting, award-winning social media visual: {prompt}"
        )
        encoded_prompt = urllib.parse.quote(enhanced_prompt[:350])
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model}&width={width}&height={height}&nologo=true&enhance=true"

        try:
            logger.info(f"Generating Facebook visual with {model.upper()} engine: {prompt[:80]}...")
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.content) > 1024:
                    with open(target_path, "wb") as f:
                        f.write(resp.content)
                    logger.info(f"Successfully saved media image: {target_path}")
                    return str(target_path)
                else:
                    logger.warning(f"Pollinations returned status {resp.status_code}. Generating fallback graphic.")
        except Exception as e:
            logger.warning(f"Image generation request failed: {e}. Falling back to styled graphic card.")

        # Offline / fallback styled graphic card
        return self._generate_svg_graphic(fallback_title, width, height, prefix, file_id)

    def _generate_svg_graphic(self, title: str, width: int, height: int, prefix: str, file_id: str) -> str:
        """Creates a modern SVG card if internet is unavailable or request times out."""
        filename = f"{prefix}_{file_id}.svg"
        target_path = MEDIA_DIR / filename
        
        safe_title = (
            title.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
        )
        
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a3d28" />
      <stop offset="50%" stop-color="#0e452e" />
      <stop offset="100%" stop-color="#021f14" />
    </linearGradient>
    <radialGradient id="glow" cx="80%" cy="20%" r="60%">
      <stop offset="0%" stop-color="#10b981" stop-opacity="0.35" />
      <stop offset="100%" stop-color="#10b981" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bg)" />
  <circle cx="{width * 0.8}" cy="{height * 0.2}" r="{width * 0.5}" fill="url(#glow)" />
  <g transform="translate({width * 0.08}, {height * 0.12})">
    <rect width="180" height="42" rx="21" fill="#10b981" fill-opacity="0.2" />
    <text x="90" y="26" fill="#10b981" font-family="system-ui, sans-serif" font-size="16" font-weight="bold" text-anchor="middle">OFFICIAL INSIGHT</text>
  </g>
  <foreignObject x="{width * 0.08}" y="{height * 0.3}" width="{width * 0.84}" height="{height * 0.5}">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-family: system-ui, -apple-system, sans-serif; color: #ffffff; font-weight: 800; font-size: {int(width * 0.045)}px; line-height: 1.25; text-shadow: 0 4px 20px rgba(0,0,0,0.5);">
      {safe_title}
    </div>
  </foreignObject>
  <text x="{width * 0.08}" y="{height * 0.92}" fill="#a7f3d0" font-family="system-ui, sans-serif" font-size="{int(width * 0.024)}" font-weight="600">
    ⚡ Ultimate Content Intelligence &bull; Facebook Growth Edition
  </text>
</svg>"""

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        return str(target_path)
