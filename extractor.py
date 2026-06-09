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
Egy magyar lakberendezési webshop (nordic-home.dk) marketingszövegírója vagy. A gyártó a House Nordic (dán bútor márka).

FONTOS STÍLUSSZABÁLYOK:
- TEGEZŐ stílus ("használd", "helyezd", "tedd") — NEM magázó
- Rövid, pörgős mondatok — max 2-3 mondat a leírásokban, NE írj 5 mondatos bekezdéseket
- Élénk, személyes hangvétel — "lélegzetelállító", "elragadó", "csempészd otthonodba"
- NE használj sablonosságokat: "letisztult skandináv design", "harmonizál", "biztosít"
- Inkább: mit csinálhatsz vele, hova tedd, milyen hangulatot teremt

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
HELYES példák: "Elegáns rózsaszín bársony puff", "Fehér skandináv stílusú függőlámpa 25 cm", "Márvány talpú bézs asztali lámpa", "Natúr tengerfű fonott kosár szett 3 db"

### short_desc (Rövid leírás)
PONTOSAN ez a formátum:
1. Terméknév.
2. 1 mondat ami TÉNYLEG elmondja MI ez és MIRE jó — NE legyen sablonos
3. Méret külön mondatban
HELYES: "Elegáns rózsaszín bársony puff. Minden szobának elragadó légkört teremt. Mérete 34x34x43 cm"
HELYES: "Márvány talpú bézs asztali lámpa. Modern és stílusos kiegészítő világítás a hálóban vagy nappaliban. Magassága 45 cm"
HELYTELEN: "Kényelmes, modern bárszék, amely tökéletes konyhaszigethez" — túl általános

### long_desc (Hosszú leírás)
HTML formátum, PONTOSAN így:

1. Kezdés: <strong>Terméknév</strong>, utána vesszővel folytatva
2. 2-3 mondat: MIT csinálhatsz vele, HOVA tedd, miért különleges — tegező stílusban
3. Méret és "Gyártó: House Nordic"

LÁMPÁKNÁL kötelezően add hozzá a végéhez:
<p>Ápolási tanácsok:</p><ul><li>A lámpát nedves ruhával tisztítsd</li></ul><p>Milyen égőt használjunk:</p><ul><li>[foglalat típusa]</li><li>[watt]</li></ul>

SZŐNYEGEKNÉL kötelezően add hozzá:
<p>Ápolási tanácsok:</p><ul><li>Rendszeresen porszívózd</li><li>Foltokat azonnal itasd fel nedves ruhával</li><li>Nem gépi mosásra tervezték</li></ul>

PÉLDA (puff):
"<strong>Elegáns rózsaszín bársony puff</strong>, amely rózsaszín bársony borítása és arany színű talpazat együttese lélegzetelállító kompozíciót alkot. Halvány színének köszönhetően pompás harmóniába hozható sötétebb színű bútorokkal, bármelyik szobába nagyszerűen mutat. Használható lábtartónak, extra ülőhelyként és még megannyi lehetőségként. Mérete 34x34x43 cm Gyártó: House Nordic"

PÉLDA (lámpa):
"<strong>Márvány talpú bézs asztali lámpa</strong>, amely gomba formájával és visszafogott bézs színével a skandináv stílust csempészi otthonodba, ugyanakkor a márvány talp és arany színű rúdja elegánssá teszi. Használd a nappaliban az olvasósarokban vagy a hálószobában. Vezeték hossza 160 cm. Az asztali lámpa átmérője 25 cm, a magassága 45 cm. Gyártó: House Nordic<p>Ápolási tanácsok:</p><ul><li>A lámpát nedves ruhával tisztítsd</li></ul><p>Milyen égőt használjunk:</p><ul><li>E14 foglalat</li><li>40 W égő</li></ul>"

PÉLDA (asztal):
"<strong>Lourmarin tölgyfa kisasztal üveg lappal</strong> – természetes tölgyfa és edzett üveg találkozása. Tedd a kanapé mellé vagy használd éjjeliszekrényként, az alsó polcra dobd a kedvenc könyveidet. Mérete 40x40x45 cm. Gyártó: House Nordic"

### product_type
Válassz EGYET ezek közül: {product_types}

### color_hu
A termék fő színe MAGYARUL. Példák: Fehér, Szürke, Natúr, Bézs, Fekete, Rózsaszín, Ezüst, Zöld, Barna
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
