#!/usr/bin/env python3
"""Real API smoke tests for optional providers.

Reads API keys from stdin so secrets do not need to be written to .env.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
import time

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.integrations.agnes_llm import AgnesLLMClient
from app.integrations.agnes_image import AgnesImageClient
from app.integrations.agnes_video import AgnesVideoClient
from app.integrations.apimart_gpt_image2 import APIMartGPTImage2Client


def read_secret(label: str) -> str:
    env_value = os.environ.get(label)
    if env_value:
        return env_value
    print(f"Paste {label} and press Enter:", file=sys.stderr)
    secret = sys.stdin.readline().strip()
    if not secret:
        raise SystemExit(f"Missing {label}")
    return secret


async def run_agnes() -> dict:
    api_key = read_secret("AGNES_API_KEY")
    base = "https://apihub.agnes-ai.com/v1"
    results = {}

    llm = AgnesLLMClient({
        "api_key": api_key,
        "base_url": base,
        "model": "agnes-2.0-flash",
        "timeout": 60,
    })
    text = await llm.chat_completion(
        messages=[{"role": "user", "content": "Reply with exactly: Agnes text ok"}],
        temperature=0,
        max_tokens=32,
    )
    results["text"] = {"ok": "Agnes text ok" in text, "sample": text[:120]}

    image = AgnesImageClient({
        "api_key": api_key,
        "base_url": base,
        "model": "agnes-image-2.1-flash",
        "size": "1024x768",
        "timeout": 180,
    })
    image_result = await image.generate_image_with_metadata(
        "A clean 9:16 storyboard frame for a TikTok ad: a minimalist desk setup with an AI app dashboard on a laptop, bright commercial lighting, no text, no watermark",
        size="1024x768",
    )
    image_url = image_result["image_url"]
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        img_resp = await client.get(image_url)
    results["image"] = {
        "ok": img_resp.status_code < 400 and len(img_resp.content) > 1000,
        "status_code": img_resp.status_code,
        "content_type": img_resp.headers.get("content-type"),
        "bytes": len(img_resp.content),
        "url_prefix": image_url[:80],
    }

    video = AgnesVideoClient({
        "api_key": api_key,
        "base_url": base,
        "model": "agnes-video-v2.0",
        "width": 512,
        "height": 512,
        "num_frames": 9,
        "frame_rate": 8,
        "poll_interval": 5,
        "timeout": 300,
    })
    task_id = await video.create_video_task(
        prompt="A short cinematic product teaser: a laptop with an AI video generation dashboard, gentle camera push in, modern bright studio lighting, no text, no watermark",
        image_url=image_url,
        storyboard_image_urls=[image_url],
        storyboard_mode="first_frame",
        seed=1,
    )
    started = time.time()
    final = None
    timeline = []
    while time.time() - started < 300:
        status = await video.get_task_result(task_id)
        timeline.append({"status": status.get("status"), "progress": status.get("progress")})
        if status.get("status") in {"completed", "succeeded", "success", "done"}:
            final = status
            break
        if status.get("status") in {"failed", "error", "cancelled", "canceled"}:
            raise RuntimeError(f"Agnes video failed: {status}")
        await asyncio.sleep(5)
    if not final:
        raise TimeoutError(f"Agnes video did not complete in 300s; timeline={timeline[-10:]}")
    video_url = final.get("video_url")
    if not video_url:
        raise RuntimeError(f"Agnes video completed but no downloadable URL was found: {final.get('raw')}")
    async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
        vid_resp = await client.get(video_url)
    results["video"] = {
        "ok": vid_resp.status_code < 400 and len(vid_resp.content) > 1000,
        "task_id": task_id,
        "timeline_tail": timeline[-10:],
        "status_code": vid_resp.status_code,
        "content_type": vid_resp.headers.get("content-type"),
        "bytes": len(vid_resp.content),
        "url_prefix": video_url[:80] if video_url else None,
    }
    return results


async def run_apimart() -> dict:
    api_key = read_secret("APIMART_API_KEY")
    client = APIMartGPTImage2Client({
        "api_key": api_key,
        "base_url": "https://api.apimart.ai",
        "model": "gpt-image-2",
        "size": "9:16",
        "resolution": "1k",
        "timeout": 300,
        "poll_interval": 5,
    })
    result = await client.generate_image_with_metadata(
        "A polished vertical TikTok ad storyboard frame of a creator reviewing an AI-generated product video on a laptop, cinematic commercial lighting, no text, no watermark"
    )
    image_url = result["image_url"]
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
        response = await http.get(image_url)
    return {
        "image": {
            "ok": response.status_code < 400 and len(response.content) > 1000,
            "task_id": result.get("task_id"),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "bytes": len(response.content),
            "url_prefix": image_url[:80],
        }
    }


async def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "agnes"
    if target == "agnes":
        payload = await run_agnes()
    elif target == "apimart":
        payload = await run_apimart()
    else:
        raise SystemExit("Usage: real_api_smoke.py [agnes|apimart]")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
