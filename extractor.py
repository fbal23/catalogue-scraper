"""Claude-powered Hungarian content generation for House Nordic products."""

import base64
import json
import re

import anthropic

PRODUCT_TYPES = [
    "szőnyeg", "lámpa", "asztal", "ülőbútor", "tárolás", "tükör",
    "párna", "takaró", "puff", "terítés", "kosár", "tálca",
    "váza és kaspó", "játék",
]

GENERATION_PROMPT = """\
Egy magyar bútorbolt webshopjába készítesz termékleírásokat. A gyártó a House Nordic (dán bútor márka).

Az alábbi termékadatok és termékkép alapján generálj magyar nyelvű tartalmat.

## Termékadatok
- Angol név: {title}
- Teljes név: {name_full}
- Anyag (EN): {material_en}
- Anyag (DA): {material_da}
- Szövet típus: {fabric_type}
- Szín (EN): {color_en}
- Szín (DA): {color_da}
- Szélesség: {width} cm
- Hosszúság: {length} cm
- Magasság: {height} cm
- Ülésmagasság: {seat_height} cm

## Feladatok

Adj vissza CSAK egy JSON objektumot (nincs markdown, nincs magyarázat):

{{
  "name_hu": "...",
  "short_desc": "...",
  "long_desc": "...",
  "product_type": "...",
  "color_hu": "..."
}}

### name_hu (Terméknév)
Rövid, figyelemfelkeltő magyar terméknév ami tartalmazza a legfontosabb jellemzőt (szín VAGY anyag).
Példák: "Elegáns rózsaszín bársony puff", "Fehér skandináv stílusú függőlámpa 25 cm", "Márvány talpú bézs asztali lámpa"

### short_desc (Rövid leírás)
Formátum:
1. Terméknév.
2. 1 mondat ami elmondja MI ez és MIRE jó.
3. Méret külön mondatban.
Példa: "Fehér skandináv stílusú függőlámpa. Letisztult, elegáns függőlámpa az otthonodban. Átmérője 25 cm"
Példa: "Elegáns rózsaszín bársony puff. Minden szobának elragadó légkört teremt. Mérete 34x34x43 cm"

### long_desc (Hosszú leírás)
HTML formátum:
- Eleje: <strong>Terméknév</strong>
- Utána SEO-barát, természetes szöveg
- Stílus: tárgyilagos + enyhén lakberendezős
- Tartalmazza: konkrét funkció, hol használja a vevő, plusz előny ha van
- Vége: méret és "Gyártó: House Nordic"
- Lámpáknál: LED esetén LED technológia, vezeték hossz ha releváns
- Szőnyegeknél: ápolási tanács (porszívózás, foltisztítás)
Példa: "<strong>Fehér skandináv stílusú függőlámpa</strong>, amely az elegáns skandináv stílust képviseli. Használj több hasonló lámpát egy csoportban a drámaibb hatás kedvéért vagy akár csak egyet a letisztult megjelenés érdekében. A függőlámpa átmérője 25 cm, magassága 22 cm. Gyártó: House Nordic"

### product_type
Válassz EGYET ezek közül: {product_types}
A kép és a terméknév alapján döntsd el.

### color_hu
A termék fő színe MAGYARUL. Példák: Fehér, Szürke, Natúr, Bézs, Fekete, Rózsaszín, Ezüst, Zöld
"""


def generate_hu_content(product_data: dict, image_bytes: bytes | None = None) -> dict:
    """Generate Hungarian product content using Claude.

    Args:
        product_data: normalized product dict from hn_lookup
        image_bytes: optional product image for visual analysis

    Returns:
        dict with name_hu, short_desc, long_desc, product_type, color_hu
    """
    client = anthropic.Anthropic()

    prompt_text = GENERATION_PROMPT.format(
        title=product_data.get("title", ""),
        name_full=product_data.get("name_full", ""),
        material_en=product_data.get("material_en", ""),
        material_da=product_data.get("material_da", ""),
        fabric_type=product_data.get("fabric_type", ""),
        color_en=product_data.get("color_en", ""),
        color_da=product_data.get("color_da", ""),
        width=product_data.get("width", ""),
        length=product_data.get("length", ""),
        height=product_data.get("height", ""),
        seat_height=product_data.get("seat_height", ""),
        product_types=", ".join(PRODUCT_TYPES),
    )

    # Build message content with optional image
    content = []
    if image_bytes:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64},
        })
    content.append({"type": "text", "text": prompt_text})

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": content}],
    )

    response_text = message.content[0].text

    # Parse JSON from response
    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not json_match:
        raise ValueError(f"Could not parse JSON from Claude response: {response_text[:200]}")

    result = json.loads(json_match.group())

    # Validate product_type
    if result.get("product_type") not in PRODUCT_TYPES:
        # Find closest match
        pt = result.get("product_type", "").lower()
        for valid_type in PRODUCT_TYPES:
            if valid_type.lower() in pt or pt in valid_type.lower():
                result["product_type"] = valid_type
                break

    return {
        "name_hu": result.get("name_hu", ""),
        "short_desc": result.get("short_desc", ""),
        "long_desc": result.get("long_desc", ""),
        "product_type": result.get("product_type", ""),
        "color_hu": result.get("color_hu", ""),
    }
