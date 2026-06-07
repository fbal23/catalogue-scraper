"""Persistent Excel catalogue builder with embedded product images."""

import io
from datetime import datetime

import httpx
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlImage
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from PIL import Image as PILImage

COLUMNS = ["Name", "Description", "Price", "Currency", "Image", "Product URL", "Source URL", "Date Added"]
THUMBNAIL_HEIGHT = 100  # pixels
ROW_HEIGHT_PTS = 80  # Excel row height in points
IMAGE_COL_WIDTH = 20  # Excel column width for image column

HEADERS_STYLE = Font(bold=True, size=11)


_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "image/*,*/*;q=0.8",
}


def download_image_bytes(url: str, timeout: float = 15.0) -> bytes | None:
    """Download an image and return raw bytes. Returns None on failure."""
    if not url:
        return None
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=_BROWSER_HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception:
        return None


def _make_thumbnail(image_bytes: bytes) -> io.BytesIO:
    """Resize image bytes to thumbnail and return as BytesIO for openpyxl."""
    with PILImage.open(io.BytesIO(image_bytes)) as img:
        # Convert to RGB if needed (handles RGBA, palette, etc.)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        # Calculate proportional width
        ratio = THUMBNAIL_HEIGHT / img.height
        new_width = int(img.width * ratio)
        img = img.resize((new_width, THUMBNAIL_HEIGHT), PILImage.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf




def build_excel(products: list[dict]) -> bytes:
    """Build an Excel file from products and return as bytes.

    Products should have 'image_bytes' key with pre-downloaded image data.

    Returns:
        Excel file as bytes
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Product Catalogue"

    # Write header row
    for col_idx, header in enumerate(COLUMNS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADERS_STYLE

    # Set column widths
    col_widths = [30, 50, 10, 8, IMAGE_COL_WIDTH, 40, 40, 12]
    for col_idx, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    image_col_idx = COLUMNS.index("Image") + 1
    today = datetime.now().strftime("%Y-%m-%d")

    for i, product in enumerate(products):
        row = i + 2  # Row 1 is header

        ws.cell(row=row, column=1, value=product["name"])
        ws.cell(row=row, column=2, value=product["description"]).alignment = Alignment(wrap_text=True)
        ws.cell(row=row, column=3, value=product["price"])
        ws.cell(row=row, column=4, value=product["currency"])
        ws.cell(row=row, column=6, value=product["product_url"])
        ws.cell(row=row, column=7, value=product.get("source_url", ""))
        ws.cell(row=row, column=8, value=today)

        # Embed image from pre-downloaded bytes
        img_bytes = product.get("image_bytes")
        if img_bytes:
            try:
                thumb_buf = _make_thumbnail(img_bytes)
                xl_img = XlImage(thumb_buf)
                cell_ref = f"{get_column_letter(image_col_idx)}{row}"
                ws.add_image(xl_img, cell_ref)
                ws.row_dimensions[row].height = ROW_HEIGHT_PTS
            except Exception:
                ws.cell(row=row, column=image_col_idx, value=product.get("image_url", ""))
        else:
            ws.cell(row=row, column=image_col_idx, value=product.get("image_url", ""))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


