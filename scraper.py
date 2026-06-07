"""HTML fetching and cleaning for product catalogue scraping."""

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,da;q=0.8",
}

MAX_HTML_LENGTH = 100_000


def fetch_page(url: str) -> str:
    """Fetch a web page and return raw HTML."""
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def clean_html(raw_html: str, base_url: str) -> str:
    """Strip non-content elements and return clean HTML suitable for LLM extraction.

    Converts relative URLs to absolute so the LLM sees full image/link paths.
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove non-content tags
    for tag_name in ("script", "style", "nav", "footer", "header", "noscript", "svg", "iframe"):
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Convert relative URLs to absolute
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            img["src"] = urljoin(base_url, src)
        srcset = img.get("srcset")
        if srcset:
            img["srcset"] = ""  # Remove srcset to simplify

    for a in soup.find_all("a"):
        href = a.get("href")
        if href:
            a["href"] = urljoin(base_url, href)

    cleaned = str(soup)

    # Truncate to stay within context limits
    if len(cleaned) > MAX_HTML_LENGTH:
        cleaned = cleaned[:MAX_HTML_LENGTH]

    return cleaned
