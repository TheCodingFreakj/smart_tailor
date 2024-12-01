import shopify

# Set up Shopify API credentials
SHOP_URL = "smarttailor324.myshopify.com"  # Replace with your store's URL
API_KEY = "ceb8830cc030a920a55c93034098563c"  # Replace with your API key
PASSWORD = "79cdf05416a53e310f67a81e6e0ee6d1"  # Replace with your password

# Connect to Shopify API
shop_url = f"https://{API_KEY}:{PASSWORD}@{SHOP_URL}/admin/api/2024-10"
shopify.ShopifyResource.set_site(shop_url)