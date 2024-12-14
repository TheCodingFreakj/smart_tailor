import requests

class ShopifyAssetManager:
    def __init__(self, shop_url, access_token):
        """
        Initialize the ShopifyAssetManager.

        :param shop_url: The base URL of the Shopify store (e.g., 'https://{shop_name}.myshopify.com/admin/api/{api_version}')
        :param access_token: The Shopify store's private access token.
        """
        self.base_url = shop_url
        self.headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }

    def get_main_theme_id(self):
        """
        Fetches the main theme ID of the Shopify store.

        :return: The ID of the main theme.
        :raises Exception: If the request fails or the main theme is not found.
        """
        url = f"{self.base_url}/themes.json"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            themes = response.json().get("themes", [])
            main_theme = next((theme for theme in themes if theme.get("role") == "main"), None)

            if main_theme:
                return main_theme["id"]
            else:
                raise Exception("Main theme not found.")
        else:
            raise Exception(f"Failed to fetch themes: {response.status_code} {response.text}")

    def delete_asset(self, key):
        """
        Deletes an asset from the main theme.

        :param key: The key of the asset to delete (e.g., 'assets/example.css').
        :return: Response message indicating success or failure.
        :raises Exception: If the request fails.
        """
        try:
            theme_id = self.get_main_theme_id()
            url = f"{self.base_url}/themes/{theme_id}/assets.json"
            params = {"asset[key]": key}

            response = requests.delete(url, params=params, headers=self.headers)

            if response.status_code == 200:
                return f"Asset '{key}' deleted successfully."
            else:
                raise Exception(f"Failed to delete asset: {response.status_code} {response.text}")

        except Exception as e:
            raise Exception(f"Error in deleting asset: {str(e)}")
        

    def get_theme_asset(self, theme_id, asset_key):
        """Fetches the content of a specific theme asset."""
        response = requests.get(
            f"{self.api_url}/themes/{theme_id}/assets.json",
            params={"asset[key]": asset_key},
            headers=self.headers
        )
        if response.status_code == 200:
            return response.json().get("asset", {}).get("value", "")
        else:
            raise Exception(f"Failed to fetch asset: {response.status_code} {response.text}")
        
            
    def remove_script_from_asset(self, asset_key, script_identifier):
        """Removes a specific piece of script from a theme asset."""

        theme_id = self.get_main_theme_id()
        # Fetch the current content
        current_content = self.get_theme_asset(theme_id, asset_key='layout/theme.liquid')
        
        # Remove the desired script (e.g., based on an identifier)
        if script_identifier in current_content:
            updated_content = current_content.replace(script_identifier, "")
        else:
            print("Script identifier not found in the content.")
            return