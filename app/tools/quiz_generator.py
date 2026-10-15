"""
Quiz Generator and Facebook Auto-Publisher for Hyper-Motion.
Generates clean, high-resolution multiple-choice quiz images (Japanese JLPT, General Knowledge, Tech, etc.)
using LLM (ChatGPT / Gemini / Nano / Banano) and Pillow, then publishes them to Facebook Page.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# Load environment configuration
load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

from app.config import get_settings
from app.llm.gateway import LLMGateway
from app.tools.facebook import FacebookClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("QuizPublisher")

FONT_CANDIDATES = [
    "C:/Windows/Fonts/YuGothB.ttc",   # Windows Yu Gothic Bold (Best for Japanese & clean typography)
    "C:/Windows/Fonts/msgothic.ttc",  # MS Gothic
    "C:/Windows/Fonts/arialbd.ttf",   # Arial Bold
    "C:/Windows/Fonts/arial.ttf"
]

def get_best_font(size: int) -> ImageFont.FreeTypeFont:
    """Select the best available TrueType/OpenType font that supports CJK & Latin."""
    for font_path in FONT_CANDIDATES:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def render_quiz_image(
    quiz_data: Dict[str, Any],
    output_path: str,
    width: int = 1080,
    height: int = 1080,
    theme: str = "minimal_white"
) -> str:
    """
    Renders pixel-perfect 1080x1080 square quiz cards matching the requested style.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    bg_color = (255, 255, 255)
    text_color = (20, 20, 20)
    accent_color = (50, 50, 50)
    
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    question_font = get_best_font(size=44)
    option_font = get_best_font(size=40)
    badge_font = get_best_font(size=26)

    # Question text
    q_num = quiz_data.get("question_number", 1)
    q_text = quiz_data.get("question", "").strip()
    full_q_text = f"{q_num}. {q_text}"

    # Draw category / level badge at top if available
    category = quiz_data.get("category") or quiz_data.get("level")
    if category:
        badge_text = f"◆ {category} QUIZ"
        draw.text((70, 180), badge_text, fill=(130, 130, 130), font=badge_font)

    # Word wrap the question text cleanly
    start_y = 300
    max_chars_per_line = 24
    lines = []
    
    # Split into lines nicely
    raw_lines = full_q_text.split("\n")
    for r_line in raw_lines:
        while len(r_line) > max_chars_per_line:
            lines.append(r_line[:max_chars_per_line])
            r_line = r_line[max_chars_per_line:]
        if r_line:
            lines.append(r_line)

    curr_y = start_y
    for line in lines:
        draw.text((70, curr_y), line, fill=text_color, font=question_font)
        curr_y += 65

    # Options spacing
    curr_y = max(curr_y + 40, 480)
    options = quiz_data.get("options", {})
    
    # Standardize options A, B, C, D
    opt_keys = ["A", "B", "C", "D"]
    if isinstance(options, dict):
        items = []
        for k in opt_keys:
            val = options.get(k) or options.get(k.lower()) or options.get(str(opt_keys.index(k) + 1))
            if val:
                items.append((k, val))
    elif isinstance(options, list):
        items = [(opt_keys[i], opt) for i, opt in enumerate(options[:4])]
    else:
        items = []

    for label, text in items:
        option_line = f"{label}. {text}"
        draw.text((70, curr_y), option_line, fill=text_color, font=option_font)
        curr_y += 105

    img.save(output_path, "PNG", quality=95)
    logger.info(f"Generated quiz image saved to: {output_path}")
    return output_path


def render_photo_quiz_image(
    quiz_data: Dict[str, Any],
    photo_path: Optional[str],
    output_path: str,
    width: int = 1080,
    height: int = 1350
) -> str:
    """
    Renders high-converting visual photographic quiz post matching standard Japanese learning formats:
    - Top: Bold sentence header with red dashed blank '----'
    - Center: Authentic high-res photographic scene representing the action/verb
    - Bottom: 4 vibrant 2x2 rounded pill badges with colored circled numbers and bold Japanese characters
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 4:5 vertical portrait aspect ratio (1080 x 1350)
    canvas = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # 1. TOP HEADER: Bold sentence
    sentence_raw = quiz_data.get("question", "").strip()
    # Normalize blank representation to standard format
    sentence_clean = re.sub(r"_{2,}|-{2,}", "----", sentence_raw)
    
    # Fonts
    header_font = get_best_font(size=64)
    option_font = get_best_font(size=66)
    num_font = get_best_font(size=46)

    # Calculate position and draw sentence at top (y: 30 to 180)
    # Split by blank "----" to draw the dashes in red for high contrast
    header_y = 65
    if "----" in sentence_clean:
        parts = sentence_clean.split("----", 1)
        part1 = parts[0].strip()
        part2 = parts[1].strip() if len(parts) > 1 else ""

        # Measure text segments
        bbox1 = draw.textbbox((0, 0), part1, font=header_font)
        w1 = bbox1[2] - bbox1[0]
        bbox_dash = draw.textbbox((0, 0), "----", font=header_font)
        w_dash = bbox_dash[2] - bbox_dash[0]
        bbox2 = draw.textbbox((0, 0), part2, font=header_font)
        w2 = bbox2[2] - bbox2[0]

        total_w = w1 + 18 + w_dash + 18 + w2
        start_x = max(40, (width - total_w) // 2)

        # Draw part1
        draw.text((start_x, header_y), part1, fill=(15, 23, 42), font=header_font)
        curr_x = start_x + w1 + 14
        # Draw red dashed blank
        draw.text((curr_x, header_y), "----", fill=(239, 68, 68), font=header_font)
        curr_x += w_dash + 14
        # Draw part2
        draw.text((curr_x, header_y), part2, fill=(15, 23, 42), font=header_font)
    else:
        # Fallback single centered text
        bbox = draw.textbbox((0, 0), sentence_clean, font=header_font)
        w = bbox[2] - bbox[0]
        draw.text(((width - w) // 2, header_y), sentence_clean, fill=(15, 23, 42), font=header_font)

    # 2. CENTER: Full-Width Scene Photo (y: 160 to 880, height: 720)
    photo_box = (0, 160, width, 880)
    photo_w = photo_box[2] - photo_box[0]
    photo_h = photo_box[3] - photo_box[1]

    if photo_path and os.path.exists(photo_path):
        try:
            with Image.open(photo_path) as p_img:
                p_img = p_img.convert("RGB")
                # Aspect crop to fit photo_w x photo_h
                src_w, src_h = p_img.size
                target_ratio = photo_w / photo_h
                src_ratio = src_w / src_h

                if src_ratio > target_ratio:
                    new_w = int(src_h * target_ratio)
                    left = (src_w - new_w) // 2
                    p_img = p_img.crop((left, 0, left + new_w, src_h))
                else:
                    new_h = int(src_w / target_ratio)
                    top = (src_h - new_h) // 2
                    p_img = p_img.crop((0, top, src_w, top + new_h))

                p_img = p_img.resize((photo_w, photo_h), Image.Resampling.LANCZOS)
                canvas.paste(p_img, (photo_box[0], photo_box[1]))
        except Exception as e:
            logger.warning(f"Failed to paste scene photo: {e}")
            draw.rectangle(photo_box, fill=(241, 245, 249))
    else:
        # Clean placeholder background if no photo generated
        draw.rectangle(photo_box, fill=(241, 245, 249))
        placeholder_font = get_best_font(size=36)
        cat_text = quiz_data.get("category", "Japanese Practice")
        draw.text((photo_box[0] + 80, photo_box[1] + 320), f"Scene Illustration: {cat_text}", fill=(100, 116, 139), font=placeholder_font)

    # 3. BOTTOM: 4 Vibrant 2x2 Rounded Options Badges (y: 915 to 1300)
    # Matching the exact viral look: white card background, colored border, solid colored number circle
    # 1: Pink (#f43f5e)
    # 2: Vibrant Blue (#0284c7)
    # 3: Emerald (#059669)
    # 4: Warm Amber / Orange (#f59e0b)
    button_themes = [
        {"circle_bg": (244, 63, 94), "border": (244, 63, 94), "pill_bg": (255, 255, 255)},
        {"circle_bg": (2, 132, 199), "border": (2, 132, 199), "pill_bg": (255, 255, 255)},
        {"circle_bg": (5, 150, 105), "border": (5, 150, 105), "pill_bg": (255, 255, 255)},
        {"circle_bg": (245, 158, 11), "border": (245, 158, 11), "pill_bg": (255, 255, 255)},
    ]

    # Parse options values
    raw_opts = quiz_data.get("options", {})
    opt_labels = ["1", "2", "3", "4"]
    opt_keys = ["A", "B", "C", "D"]
    opt_values = []
    
    if isinstance(raw_opts, dict):
        for idx, k in enumerate(opt_keys):
            val = raw_opts.get(k) or raw_opts.get(k.lower()) or raw_opts.get(str(idx + 1)) or ""
            opt_values.append(str(val).strip())
    elif isinstance(raw_opts, list):
        opt_values = [str(x).strip() for x in raw_opts[:4]]
    
    while len(opt_values) < 4:
        opt_values.append("")

    # Grid configuration for 2 columns, 2 rows
    margin_x = 44
    gap_x = 24
    card_w = (width - (margin_x * 2) - gap_x) // 2  # ~484px
    card_h = 165
    gap_y = 22
    base_y = 930

    positions = [
        (margin_x, base_y),                                # Row 1, Col 1
        (margin_x + card_w + gap_x, base_y),               # Row 1, Col 2
        (margin_x, base_y + card_h + gap_y),               # Row 2, Col 1
        (margin_x + card_w + gap_x, base_y + card_h + gap_y)# Row 2, Col 2
    ]

    for i in range(4):
        bx, by = positions[i]
        theme = button_themes[i]
        badge_num = opt_labels[i]
        opt_char = opt_values[i]

        # Draw rounded rectangle container
        draw.rounded_rectangle(
            [bx, by, bx + card_w, by + card_h],
            radius=34,
            fill=theme["pill_bg"],
            outline=theme["border"],
            width=3
        )

        # Draw colored circle for number on the left
        circle_diameter = 90
        circle_x = bx + 22
        circle_y = by + (card_h - circle_diameter) // 2
        draw.ellipse(
            [circle_x, circle_y, circle_x + circle_diameter, circle_y + circle_diameter],
            fill=theme["circle_bg"]
        )

        # Draw number in white inside circle
        n_bbox = draw.textbbox((0, 0), badge_num, font=num_font)
        nw = n_bbox[2] - n_bbox[0]
        nh = n_bbox[3] - n_bbox[1]
        nx = circle_x + (circle_diameter - nw) // 2
        ny = circle_y + (circle_diameter - nh) // 2 - 4
        draw.text((nx, ny), badge_num, fill=(255, 255, 255), font=num_font)

        # Draw bold Japanese character / word on the right
        # Strip any accidental 'A.', '1.' prefixes
        opt_char_clean = re.sub(r"^[A-Da-d1-4][\.\s、]+", "", opt_char).strip()
        c_bbox = draw.textbbox((0, 0), opt_char_clean, font=option_font)
        cw = c_bbox[2] - c_bbox[0]
        ch = c_bbox[3] - c_bbox[1]
        # Center in the remaining space (from circle_x + circle_diameter to bx + card_w)
        remain_start = circle_x + circle_diameter
        remain_w = (bx + card_w) - remain_start
        cx = remain_start + (remain_w - cw) // 2
        cy = by + (card_h - ch) // 2 - 6
        draw.text((cx, cy), opt_char_clean, fill=(15, 23, 42), font=option_font)

    canvas.save(output_path, "PNG", quality=95)
    logger.info(f"Generated photographic visual quiz saved to: {output_path}")
    return output_path


class QuizService:
    def __init__(self):
        self.gateway = LLMGateway()
        self.fb_client = FacebookClient()

    async def generate_quiz_content(
        self,
        topic: str = "JLPT N5 Japanese Grammar",
        q_number: int = 27
    ) -> Dict[str, Any]:
        """Generate multiple choice question using LLM (ChatGPT / Gemini / Nano)."""
        prompt = f"""
Generate an engaging multiple-choice quiz question for topic: '{topic}'.
Question number: {q_number}.

Important instructions:
- If the topic is Japanese (JLPT, Kana, Kanji), keep the question and options in Japanese script (Hiragana/Katakana/Kanji like sample: 'A. に', 'B. を', 'C. で', 'D. と'), do not use romaji unless specifically requested.
- Keep the question concise and authentic to JLPT standard test format with blank '______'.

Format strictly as JSON with this schema:
{{
  "question_number": {q_number},
  "category": "{topic}",
  "question": "Sentence with blank '______' to fill in",
  "options": {{
    "A": "Option A in native script",
    "B": "Option B in native script",
    "C": "Option C in native script",
    "D": "Option D in native script"
  }},
  "correct_answer": "B",
  "explanation": "Brief explanation in English why this answer is correct",
  "visual_photo_prompt": "A vivid, authentic, cinematic photo describing the action or scene in the sentence (e.g. 'A young Japanese man running along a sunny countryside road with green rice fields on a clear summer day, high resolution, realistic photography')",
  "hashtags": ["#JapaneseQuiz", "#LearnJapanese", "#JLPTN5", "#Nihongo", "#JapaneseGrammar", "#StudyJapanese"],
  "seo_keywords": ["learn japanese", "jlpt n5 quiz", "japanese grammar test", "nihongo practice"],
  "post_caption": "Engaging, SEO-rich Facebook post caption that includes an attention-grabbing hook, the question context, a clear engagement call to action asking for A/B/C/D in the comments, and concludes with 5-7 targeted hashtags (#Japanese #LearnJapanese #JLPT #JLPTN5 #Nihongo #StudyJapanese #Quiz) at the very bottom."
}}

Output ONLY raw valid JSON, no markdown codeblocks, no commentary.
"""
        raw_res = await self.gateway.generate_text(
            prompt=prompt,
            system_instruction="You are an expert educational quiz creator. Return strictly valid JSON."
        )

        clean_json = re.sub(r"^```(?:json)?", "", raw_res.strip(), flags=re.MULTILINE)
        clean_json = re.sub(r"```$", "", clean_json.strip(), flags=re.MULTILINE).strip()

        try:
            quiz = json.loads(clean_json)
        except Exception as e:
            logger.warning(f"Failed to parse JSON directly ({e}), extracting object via regex...")
            match = re.search(r"\{.*\}", clean_json, re.DOTALL)
            if match:
                quiz = json.loads(match.group(0))
            else:
                raise ValueError(f"Could not parse quiz output: {raw_res}")

        return quiz

    async def create_and_publish_quiz(
        self,
        topic: str = "JLPT N5 Japanese Grammar",
        q_number: int = 27,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Generate quiz, render image, and publish to Facebook."""
        logger.info(f"Generating quiz for topic: {topic} (# {q_number})...")
        quiz_data = await self.generate_quiz_content(topic, q_number)

        output_dir = Path("output/quizzes")
        output_dir.mkdir(parents=True, exist_ok=True)
        image_path = str(output_dir / f"quiz_{q_number}_{int(asyncio.get_event_loop().time())}.png")

        render_quiz_image(quiz_data, image_path)

        caption = quiz_data.get("post_caption") or (
            f"🧠 Daily Quiz: {topic} (#{q_number})!\n\n"
            f"Can you solve this? Test your knowledge!\n"
            f"Drop your answer (A, B, C, or D) in the comments below! 👇\n\n"
            f"#Quiz #Japanese #Learning #Language #JLPT"
        )

        if dry_run:
            logger.info("Dry run specified. Skipping Facebook publication.")
            return {
                "success": True,
                "quiz": quiz_data,
                "image_path": image_path,
                "published": False,
                "note": "Dry run complete."
            }

        logger.info("Publishing quiz post to Facebook Page...")
        fb_res = await self.fb_client.publish_photo_post(
            caption=caption,
            image_path=image_path
        )

        return {
            "success": fb_res.get("success", False),
            "quiz": quiz_data,
            "image_path": image_path,
            "facebook_response": fb_res
        }

async def main():
    parser = argparse.ArgumentParser(description="Create Quiz Image & Publish to Facebook")
    parser.add_argument("--topic", type=str, default="JLPT N5 Japanese Grammar", help="Topic of the quiz")
    parser.add_argument("--number", type=int, default=27, help="Question number")
    parser.add_argument("--dry-run", action="store_true", help="Generate image without posting to Facebook")
    args = parser.parse_args()

    service = QuizService()
    result = await service.create_and_publish_quiz(
        topic=args.topic,
        q_number=args.number,
        dry_run=args.dry_run
    )
    print("\n" + "=" * 50)
    print("QUIZ AUTOMATION EXECUTION SUMMARY:")
    print("=" * 50)
    print(f"Topic: {args.topic}")
    print(f"Question: {result['quiz']['question']}")
    print(f"Options: {result['quiz']['options']}")
    print(f"Correct Answer: {result['quiz'].get('correct_answer')}")
    print(f"Image saved at: {result['image_path']}")
    if "facebook_response" in result:
        print(f"Facebook Status: {result['facebook_response']}")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
