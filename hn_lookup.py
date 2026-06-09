"""House Nordic product lookup — fetch structured data from housenordic.dk."""

import json
import re

import httpx

PRODUCT_URL = "https://housenordic.dk/en/item/{sku}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,da;q=0.8",
}


def _parse_height_from_name(name: str) -> str | None:
    """Extract height from Name1 field like 'Sana Puf, grå, ø38x40 cm'."""
    # Match patterns like "ø38x40", "70X40", "34x34x43"
    match = re.search(r"[\dø]+[xX×](\d+(?:[xX×]\d+)?)\s*cm", name or "")
    if match:
        parts = match.group(1).split("x") if "x" in match.group(1).lower() else [match.group(1)]
        return parts[-1]  # Last number is typically height
    return None


def fetch_product(sku: str | int) -> dict | None:
    """Fetch product data from housenordic.dk by manufacturer SKU.

    Returns normalized dict or None if product not found.
    """
    url = PRODUCT_URL.format(sku=sku)
    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception:
        return None

    # Extract :prop-item JSON from Vue component attribute
    match = re.search(r':prop-item="(\{.*?\})"', html)
    if not match:
        return None

    try:
        raw_json = match.group(1).replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        data = json.loads(raw_json)
    except (json.JSONDecodeError, ValueError):
        return None

    # Extract image URLs
    images = []
    for img in data.get("item_images", []):
        full_path = img.get("FullPath", "")
        if full_path:
            images.append(full_path)
    if not images:
        images = data.get("Thumbnails", [])

    primary_image = data.get("ImageUrl", "")
    if not primary_image and images:
        primary_image = images[0]

    # Dimensions
    width = data.get("Width") or data.get("AttBreddeENU") or ""
    length = data.get("Length") or data.get("AttLengthENU") or ""
    height = data.get("Height") or data.get("AttHeightENU") or ""

    # Height fallback: parse from Name1
    if not height:
        height = _parse_height_from_name(data.get("Name1", "")) or ""

    return {
        "sku": str(data.get("Number", sku)),
        "title": data.get("Title", ""),
        "name_full": data.get("Name1", ""),
        "material_en": data.get("AttMaterialeENU") or data.get("Material") or "",
        "material_da": data.get("AttMaterialeDAN") or "",
        "color_en": data.get("AttFarveENU") or data.get("Farve") or "",
        "color_da": data.get("AttFarveDAN") or "",
        "fabric_type": data.get("Stoftype") or data.get("AttStoftypeENU") or "",
        "width": str(width),
        "length": str(length),
        "height": str(height),
        "seat_height": str(data.get("SeatHeight") or ""),
        "weight": str(data.get("Weight") or ""),
        "barcode": data.get("Barcode") or "",
        "primary_image": primary_image,
        "images": images,
        "short_desc": data.get("WebDescENUShortDescriptionEXT") or data.get("ShortDescription") or "",
    }


def download_product_image(url: str, timeout: float = 15.0) -> bytes | None:
    """Download product image for AI analysis."""
    if not url:
        return None
    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception:
        return None
