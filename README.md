# Product Catalogue Scraper

A simple web app that extracts product data (name, description, price, images) from furniture factory websites and saves them to a single Excel catalogue.

## Setup

1. **Get an API key** from [console.anthropic.com](https://console.anthropic.com/) (costs ~$0.01-0.05 per page scraped)

2. **Create a `.env` file** in this folder:
   ```
   ANTHROPIC_API_KEY=sk-ant-...your-key-here...
   ```

3. **Install dependencies** (one time):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Run the app**:
   ```bash
   source .venv/bin/activate
   streamlit run app.py
   ```
   A browser window will open automatically.

## How to Use

1. Paste a factory product page URL (e.g. `https://www.nordic-home.dk/moebler-shop/`)
2. Click **"Scrape & Add to Catalogue"**
3. Wait ~10-20 seconds while the AI extracts products
4. Products are added to your Excel file at `~/Documents/product-catalogue.xlsx`
5. Images are saved to `~/Documents/catalogue-images/`
6. Repeat for each factory website — products keep accumulating in the same Excel file

## Excel Columns

| Column | Description |
|--------|-------------|
| Name | Product name |
| Description | Short summary (materials, dimensions, features) |
| Price | Numeric price |
| Currency | DKK, EUR, etc. |
| Image | Embedded thumbnail |
| Product URL | Link to product page |
| Source URL | The page you scraped |
| Date Added | When you added it |

## Troubleshooting

- **"Missing ANTHROPIC_API_KEY"** → Make sure your `.env` file exists with a valid key
- **No products found** → Some websites load products with JavaScript; this tool works best with server-rendered pages
- **Images missing** → Some sites block image downloads; the URL will be shown as text instead
