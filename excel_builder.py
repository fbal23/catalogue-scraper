"""Persistent Excel catalogue builder with embedded product images."""

import hashlib
import io
from datetime import datetime
from pathlib import Path

import httpx
from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image as XlImage
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from PIL import Image as PILImage

COLUMNS = ["Name", "Description", "Price", "Currency", "Image", "Product URL", "Source URL", "Date Added"]
THUMBNAIL_HEIGHT = 100  # pixels
ROW_HEIGHT_PTS = 80  # Excel row height in points
IMAGE_COL_WIDTH = 20  # Excel column width for image column

HEADERS_STYLE = Font(bold=True, size=11)


def _download_image(url: str, image_dir: Path, timeout: float = 15.0) -> Path | None:
    """Download an image and save to image_dir. Returns path or None on failure."""
    if not url:
        return None
    try:
        # Use URL hash as filename to avoid duplicates
        ext = Path(url.split("?")[0]).suffix or ".jpg"
        filename = hashlib.md5(url.encode()).hexdigest()[:12] + ext
        filepath = image_dir / filename

        if filepath.exists():
            return filepath

        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            filepath.write_bytes(resp.content)
        return filepath
    except Exception:
        return None


def _make_thumbnail(image_path: Path) -> io.BytesIO:
    """Resize image to thumbnail and return as BytesIO for openpyxl."""
    with PILImage.open(image_path) as img:
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


def _ensure_workbook(excel_path: Path) -> tuple[Workbook, int]:
    """Load existing workbook or create new one. Returns (workbook, next_row)."""
    if excel_path.exists():
        wb = load_workbook(excel_path)
        ws = wb.active
        next_row = ws.max_row + 1
        return wb, next_row
    else:
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

        return wb, 2


def append_products(
    products: list[dict],
    source_url: str,
    excel_path: Path,
    image_dir: Path,
    on_progress: callable = None,
) -> int:
    """Append products to the persistent Excel catalogue.

    Args:
        products: List of product dicts from extractor
        source_url: The URL that was scraped
        excel_path: Path to the .xlsx file
        image_dir: Directory to store downloaded images
        on_progress: Optional callback(current, total) for progress updates

    Returns:
        Number of products added
    """
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    wb, next_row = _ensure_workbook(excel_path)
    ws = wb.active
    today = datetime.now().strftime("%Y-%m-%d")

    image_col_idx = COLUMNS.index("Image") + 1  # 1-based

    for i, product in enumerate(products):
        row = next_row + i

        # Write text data
        ws.cell(row=row, column=1, value=product["name"])
        ws.cell(row=row, column=2, value=product["description"]).alignment = Alignment(wrap_text=True)
        ws.cell(row=row, column=3, value=product["price"])
        ws.cell(row=row, column=4, value=product["currency"])
        # Column 5 = Image (handled below)
        ws.cell(row=row, column=6, value=product["product_url"])
        ws.cell(row=row, column=7, value=source_url)
        ws.cell(row=row, column=8, value=today)

        # Download and embed image
        img_path = _download_image(product.get("image_url", ""), image_dir)
        if img_path:
            try:
                thumb_buf = _make_thumbnail(img_path)
                xl_img = XlImage(thumb_buf)
                cell_ref = f"{get_column_letter(image_col_idx)}{row}"
                ws.add_image(xl_img, cell_ref)
                ws.row_dimensions[row].height = ROW_HEIGHT_PTS
            except Exception:
                ws.cell(row=row, column=image_col_idx, value=product.get("image_url", ""))
        else:
            ws.cell(row=row, column=image_col_idx, value=product.get("image_url", ""))

        if on_progress:
            on_progress(i + 1, len(products))

    wb.save(excel_path)
    return len(products)


def get_total_rows(excel_path: Path) -> int:
    """Get total number of product rows in the catalogue."""
    if not excel_path.exists():
        return 0
    wb = load_workbook(excel_path, read_only=True)
    ws = wb.active
    total = ws.max_row - 1  # Subtract header row
    wb.close()
    return max(0, total)
