"""
Pexels rasm servisi.

Mavzuga / slayd kalit so'ziga mos professional rasmni Pexels (bepul stock) orqali
qidirib, vaqtinchalik papkaga yuklab oladi. Rasm topilmasa yoki API kalit
bo'lmasa — None qaytaradi (prezentatsiya baribir rasmsiz tayyorlanadi).

.env faylga PEXELS_API_KEY ni qo'shing:
    PEXELS_API_KEY=siz_olgan_kalit
Bepul kalitni https://www.pexels.com/api/ saytidan olasiz.
"""

import os
import uuid
import asyncio

import httpx

PEXELS_API_URL = "https://api.pexels.com/v1/search"


def _get_api_key() -> str | None:
    return os.environ.get("PEXELS_API_KEY")


async def fetch_image(query: str, save_dir: str, orientation: str = "landscape") -> str | None:
    """
    Berilgan kalit so'z bo'yicha bitta rasmni yuklab oladi va fayl yo'lini qaytaradi.

    query: inglizcha qidiruv so'zi (masalan, "artificial intelligence education")
    save_dir: rasm saqlanadigan papka
    orientation: 'landscape' | 'portrait' | 'square'
    """
    api_key = _get_api_key()
    if not api_key:
        print("⚠️ PEXELS_API_KEY topilmadi — rasm o'tkazib yuborildi.")
        return None

    if not query or not query.strip():
        return None

    headers = {"Authorization": api_key}
    params = {
        "query": query.strip(),
        "per_page": 1,
        "orientation": orientation,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(PEXELS_API_URL, headers=headers, params=params)
            if resp.status_code != 200:
                print(f"⚠️ Pexels qidiruv xatosi ({resp.status_code}) — '{query}'")
                return None

            data = resp.json()
            photos = data.get("photos") or []
            if not photos:
                print(f"⚠️ Pexels'da rasm topilmadi — '{query}'")
                return None

            src = photos[0].get("src", {})
            # Sifati o'rtacha, hajmi maqbul varianti
            image_url = src.get("large") or src.get("medium") or src.get("original")
            if not image_url:
                return None

            img_resp = await client.get(image_url)
            if img_resp.status_code != 200:
                return None

            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, f"img_{uuid.uuid4().hex[:8]}.jpg")
            with open(file_path, "wb") as f:
                f.write(img_resp.content)

            print(f"✅ Pexels rasm yuklandi: '{query}' -> {file_path}")
            return file_path

    except Exception as e:
        print(f"⚠️ Pexels rasm olishda xato ('{query}'): {e}")
        return None
