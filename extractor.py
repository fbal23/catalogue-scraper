"""Claude-powered product data extraction from HTML."""

import json
import re
from urllib.parse import urljoin

import anthropic

EXTRACTION_PROMPT = """\
You are a product data extraction assistant. Analyze the HTML below and extract every product you can find.

Return ONLY a valid JSON array (no markdown, no explanation) with this structure:
[
  {
    "name": "Product Name",
    "description": "Short 1-2 sentence description: materials, dimensions, key features.",
    "price": "1234.00",
    "currency": "DKK",
    "image_url": "https://example.com/image.jpg",
    "product_url": "https://example.com/product-page"
  }
]

Rules:
- Use absolute URLs for image_url and product_url (they should already be absolute in the HTML).
- price should be numeric string without currency symbol (e.g. "1234.00" not "1.234,00 DKK").
- currency should be the ISO code (DKK, EUR, SEK, etc.).
- description: summarize materials, size, style, or key features in 1-2 sentences.
- Skip navigation items, banners, ads — only extract actual products.
- If a product has no price visible, set price to "" and currency to "".
- If a product has multiple images, pick the main/first one.
"""


def extract_products(html: str, source_url: str) -> list[dict]:
    """Send cleaned HTML to Claude and get structured product data back."""
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"{EXTRACTION_PROMPT}\n\nSource page URL: {source_url}\n\n<html>\n{html}\n</html>",
            }
        ],
    )

    response_text = message.content[0].text

    # Extract JSON from response (handle potential markdown wrapping)
    json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
    if not json_match:
        raise ValueError(f"Could not parse JSON from Claude response: {response_text[:200]}")

    products = json.loads(json_match.group())

    # Validate and clean up
    cleaned = []
    for p in products:
        product = {
            "name": str(p.get("name", "")).strip(),
            "description": str(p.get("description", "")).strip(),
            "price": str(p.get("price", "")).strip(),
            "currency": str(p.get("currency", "")).strip(),
            "image_url": str(p.get("image_url", "")).strip(),
            "product_url": str(p.get("product_url", "")).strip(),
        }
        # Only include if we have at least a name
        if product["name"]:
            cleaned.append(product)

    return cleaned
