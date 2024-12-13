

import json
import re
import requests
from smarttailor import settings


class ShopifyThemeHelper:
    def __init__(self, shop, api_version="2024-10"):
        print(f"shop_id---->{shop}")
        self.shop = shop
        self.api_version = api_version
        self.headers = {"X-Shopify-Access-Token": self.shop.access_token}
        self.base_url = f"https://{self.shop.shop_name}/admin/api/{self.api_version}"

    def get_main_theme_id(self):
        """Fetches the main theme ID."""
        url = f"{self.base_url}/themes.json"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            themes = response.json().get("themes", [])
            main_theme = [theme for theme in themes if theme.get("role") == "main"]
            if main_theme:
                return main_theme[0]["id"]
            else:
                raise Exception("Main theme not found")
        else:
            raise Exception(f"Failed to fetch themes: {response.status_code} {response.text}")

    def get_theme_liquid_content(self, theme_id):
        """Fetches the `theme.liquid` content."""
        url = f"{self.base_url}/themes/{theme_id}/assets.json"
        params = {"asset[key]": "layout/theme.liquid"}
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            return response.json().get("asset", {}).get("value")
        else:
            raise Exception(f"Failed to fetch theme.liquid: {response.status_code} {response.text}")

    def update_theme_liquid(self, theme_id, updated_content, key_url):
        """Updates the `theme.liquid` content."""
        url = f"{self.base_url}/themes/{theme_id}/assets.json"
        asset_data = {
            "asset": {
                "key": key_url,
                "value": updated_content,
            }
        }

        params = {'asset[key]': key_url}

        response_get = requests.get(url, params=params,headers=self.headers)
        print(response_get.status_code)

        if response_get.status_code == 200:
            assets = response_get.json().get('asset', {}).get('value')
            print(assets)
            if assets:
                params = {
                    "asset[key]": key_url
                }
                response = requests.delete(url, params=params,headers={
        "X-Shopify-Access-Token": self.shop.access_token,
        
    })
                if response.status_code == 200:
                    print(f"Successfully deleted {key_url}")

                    response = requests.put(url, headers=self.headers, json=asset_data)
                    if response.status_code == 200:
                        print(f"Successfully uploaded {asset_data}")
                    else:
                        print(f"Failed to upload {asset_data}: {response.text}")
                else:
                    print(f"Error deleting file {key_url}: {response.text}")

        else:
            print(f"First upload")
            
            response = requests.put(url, headers=self.headers, json=asset_data)
            if response.status_code == 200:
                print(f"Successfully uploaded {asset_data}")
            else:
                print(f"Failed to upload {asset_data}: {response.text}")
    def write_theme_asset(self,api_url, theme_id, asset_key, new_content):

        payload = {
            "asset": {
                "key": asset_key,
                "value": new_content
            }
        }

        response = requests.put(f'{api_url}/themes/{theme_id}/assets.json', json=payload, headers=self.headers)

        if response.status_code == 201 or response.status_code == 200:
            print('Successfully created/updated the theme asset')
        else:
            print(f'Error: {response.status_code} - {response.text}')

    def extract_json_from_content(self, content, variable_name):
        """
        Extracts the JSON-like value of a specific variable (config_data_json or json_output) from the content.
        """
        
        print(variable_name)
        # This regex assumes that the JSON is assigned to a variable in a Liquid template
        pattern = rf"{{% assign {variable_name} = '(.+?)' %}}"
        match = re.search(pattern, content)
        print(match.group(1))
        if match:
            return match.group(1)
        return None
    def remove_recommendation_snippet(self, file_content):
            """
            Removes the block of code that assigns config_data_json and json_output and renders the recommendationshtml snippet.
            """
            # Regular expression to find and remove the block of code
            snippet_pattern = r"\{\%\s*if\s*template\s*!=\s*'index'\s*\%\}.*?\{\%\s*endif\s*\%\}"
            
            # Use re.sub to remove the snippet block
            updated_content = re.sub(snippet_pattern, '', file_content, flags=re.DOTALL)
            
            return updated_content
    def inject_json_data(self, html_encoded_content,config_data_json, json_output):
        """
        Injects the JSON data into the HTML content before rendering.
        """

  

        # Replace placeholders in the HTML content with the JSON data
        updated_content = html_encoded_content

        # Example: Add JSON data to the <script> tag
        updated_content = re.sub(r'window.config_data_json = .*?;', f'window.config_data_json = {config_data_json};', updated_content)
        updated_content = re.sub(r'window.json_output = .*?;', f'window.json_output = {json_output};', updated_content)

        # Return the updated content with JSON data injected
        return updated_content    
                 
    def inject_script_to_theme(self, config_data_json,renderedhtml,json_output, customer):
        """Injects a script to the `theme.liquid` file for a specific page."""
        try:
            theme_id = self.get_main_theme_id()
            # theme_content = self.get_theme_liquid_content(theme_id)

            # # Add the script conditionally based on the page handle
            # conditional_script = script_content

            print("mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm")


            with open('assests/slider-content.liquid', 'r') as file:
               file_content2_liq = file.read()
            html_encoded1_content = file_content2_liq

            with open('assests/round-button-slider.css', 'r') as file:
               file_content_css = file.read()
            css_encoded_content = file_content_css
            with open('assests/round-button-slider.js', 'r') as file:
               file_content_js = file.read()
            js_encoded_content = file_content_js
            html_encoded_content = None
            if renderedhtml == '':
                with open('assests/round-button-slider.liquid', 'r') as file:
                    file_content = file.read()
                    html_encoded_content = file_content
            else:
                app_url = f"{settings.SHOPIFY_APP_URL}/slider-settings/"
                params = {"customer": customer}
                responsesettings = requests.get(app_url,params=params)
                print(responsesettings.json())
                html_encoded_content = responsesettings.json()["renderedhtml"]


            # updated_html_content =self.inject_json_data(html_encoded_content,config_data_json, json_output)
            print(f"updated_html_content---------->{html_encoded1_content}")
            
            app_url = f"{settings.SHOPIFY_APP_URL}/slider-settings/"
            payloadFor={
                "customer": customer,
                "settings": config_data_json,
                "renderedhtml": html_encoded_content

            }
            responsesettings = requests.post(app_url,json=payloadFor)
            print(responsesettings.json())


            url = f"{self.base_url}/themes/{theme_id}/assets.json"

            params = {'asset[key]': 'layout/theme.liquid'}

            response_get = requests.get(url, params=params,headers=self.headers)
            asset_content = response_get.json().get('asset', {}).get('value')

            print("mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm")
            print(asset_content)
            print("mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm")
            print(response_get.status_code)

 

        # Check if the current config_data_json and json_output are different from the new ones
            
            print("Values have changed. Proceeding with the update.")

            print("dddddddddddddddddddddddddddddddddddddddddddddddddddddddddd")
            print(json.dumps(config_data_json, indent=4))
            print("dddddddddddddddddddddddddddddddddddddddddddddddddddddddddd")
            print(json.dumps(json_output, indent=4))

            json_final_settings = json.dumps(config_data_json)
            json_final_data = json.dumps(json_output)
            print("hjgjgjghhgggggggggggggggggggggg")
            print(config_data_json)
            

            # If values changed, update the theme snippet and the theme layout
            script_content = f"""
                {{% if template != 'index' %}}
                  {{% section 'round-button-slider' %}}
                    {{% endif %}}
                """
            file_content = self.get_theme_liquid_content(theme_id)
            

            if "{% if template != 'index' %}" in response_get.json().get('asset', {}).get('value'):
                    updated_content = self.remove_recommendation_snippet(file_content)
                    # Add script content just before the </body> tag
                    body_close_index = updated_content.rfind('</body>')
                    file_content = updated_content[:body_close_index] + f"\n{script_content}\n" + updated_content[body_close_index:]

                    
                    self.update_theme_liquid(theme_id, html_encoded1_content, key_url="snippets/slider-content.liquid")
                    self.update_theme_liquid(theme_id, html_encoded_content, key_url="sections/round-button-slider.liquid")
                    self.write_theme_asset(self.base_url, theme_id, 'layout/theme.liquid', file_content)
            else:

                # Add script content just before the </body> tag
                    body_close_index = file_content.rfind('</body>')
                    file_content = file_content[:body_close_index] + f"\n{script_content}\n" + file_content[body_close_index:]
                    self.update_theme_liquid(theme_id, html_encoded1_content, key_url="snippets/slider-content.liquid")
                    self.update_theme_liquid(theme_id, html_encoded_content, key_url="sections/round-button-slider.liquid")
                    self.write_theme_asset(self.base_url, theme_id, 'layout/theme.liquid', file_content)


            # self.update_theme_liquid(theme_id, css_encoded1_content,key_url="assets/slider-content.css")
            self.update_theme_liquid(theme_id, css_encoded_content,key_url="assets/round-button-slider.css")
            self.update_theme_liquid(theme_id, js_encoded_content,key_url="assets/round-button-slider.js")

            
            # self.update_theme_liquid(theme_id, file_content, key_url="layout/theme.liquid")
            
            return {"message": "Script injected successfully"}
        except Exception as e:
            return {"error": str(e)}