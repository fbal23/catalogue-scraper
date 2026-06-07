"""Product Catalogue Scraper — Streamlit Web App."""

import os

import streamlit as st
from dotenv import load_dotenv

from scraper import fetch_page, clean_html
from extractor import extract_products
from excel_builder import build_excel, download_image_bytes

load_dotenv()

# --- Page Config ---
st.set_page_config(page_title="Product Catalogue Scraper", page_icon="📦", layout="wide")
st.title("📦 Product Catalogue Scraper")
st.caption("Paste a factory product page URL → extract products → add to your catalogue")

# --- Session state for accumulating products across scrapes ---
if "all_products" not in st.session_state:
    st.session_state.all_products = []
if "last_scrape" not in st.session_state:
    st.session_state.last_scrape = None

# --- Sidebar Config ---
with st.sidebar:
    st.header("Settings")

    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

    st.divider()
    st.metric("Products scraped this session", len(st.session_state.all_products))

    if st.button("🗑️ Clear session"):
        st.session_state.all_products = []
        st.session_state.last_scrape = None
        st.rerun()

# --- Main Area ---
url = st.text_input("Factory product page URL", placeholder="https://www.example.com/products")

if st.button("🔍 Scrape & Add to Catalogue", type="primary", disabled=not url):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("Paste your Anthropic API Key in the sidebar first.")
        st.stop()

    try:
        with st.status("Fetching page...", expanded=True) as status:
            st.write(f"Downloading: {url}")
            raw_html = fetch_page(url)
            st.write(f"Got {len(raw_html):,} characters of HTML")

            status.update(label="Cleaning HTML...")
            st.write("Stripping scripts, navigation, footers...")
            cleaned = clean_html(raw_html, url)
            st.write(f"Cleaned to {len(cleaned):,} characters")

            status.update(label="Extracting products with AI...")
            st.write("Sending to Claude for product extraction...")
            products = extract_products(cleaned, url)
            st.write(f"Found **{len(products)}** products")

            # Download images and store bytes in each product dict
            status.update(label="Downloading product images...")
            for i, p in enumerate(products):
                p["source_url"] = url
                p["image_bytes"] = download_image_bytes(p.get("image_url", ""))
                st.write(f"Image {i+1}/{len(products)}: {'✓' if p['image_bytes'] else '✗'}")

            st.session_state.all_products.extend(products)
            st.session_state.last_scrape = len(products)
            status.update(label=f"Done! Found {len(products)} products", state="complete")

        st.success(f"Added **{len(products)}** products (session total: **{len(st.session_state.all_products)}**)")

    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)

# --- Catalogue display and download (always reflects current session state) ---
if st.session_state.all_products:
    st.divider()
    st.subheader(f"Full Catalogue ({len(st.session_state.all_products)} products)")

    full_data = [
        {
            "Name": p["name"],
            "Description": p["description"][:60] + ("..." if len(p["description"]) > 60 else ""),
            "Price": f"{p['price']} {p['currency']}".strip(),
            "Source": p.get("source_url", "")[:40] + "...",
            "Image": "✓" if p.get("image_bytes") else "✗",
        }
        for p in st.session_state.all_products
    ]
    st.dataframe(full_data, use_container_width=True)

    # Download button — built AFTER session state is fully updated
    excel_bytes = build_excel(st.session_state.all_products)
    st.download_button(
        "⬇️ Download catalogue (.xlsx)",
        data=excel_bytes,
        file_name="product-catalogue.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
