import requests
from smarttailor import settings
from .shopify_theme_helper import ShopifyThemeHelper
from .shopify_data_fetcher import ShopifyDataFetcher

class ShopifySliderManager:
    def __init__(self, shop, version, activity_data):
        self.shop = shop
        self.version = version
        self.activity_data = activity_data
        self.helper = ShopifyThemeHelper(shop)
        self.fetcher = ShopifyDataFetcher(shop, version, activity_data)
        self.config_data = self.get_default_config()

    def get_default_config(self):
        # Default slider configuration
        return {
            "name": "Round Button with Slider",
            "settings": [
                {"type": "text", "id": "button_text", "label": "Button Text", "default": "Open Slider"},
                {"type": "textarea", "id": "slider_content", "label": "Slider Content", "default": "Add your slider content here."},
                {"type": "color", "id": "button_color", "label": "Button Background Color", "default": "#000000"},
                {"type": "color", "id": "button_text_color", "label": "Button Text Color", "default": "#ffffff"},
                {"type": "color", "id": "slider_background", "label": "Slider Background Color", "default": "#ffffff"}
            ]
        }

    def fetch_slider_settings(self):
        url = f"{settings.SHOPIFY_APP_URL}/slider-settings/"
        params = {"customer": self.activity_data["customerId"]}
        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch settings. Status code: {response.status_code}")
            print("Error:", response.text)
            return None

    def create_slider_settings(self):
        url = f"{settings.SHOPIFY_APP_URL}/slider-settings/"
        payload = {
            "customer": self.activity_data["customerId"],
            "settings": self.config_data,
            "renderedhtml": self.get_slider_html()
        }
        response = requests.post(url, json=payload)
        return response.json() if response.status_code == 200 else None

    def get_slider_html(self):
        return """
        {% schema %}
        {
          "name": "Round Button with Slider",
          "settings": [
            {"type": "text", "id": "button_text", "label": "Button Text", "default": "Open Slider"},
            {"type": "textarea", "id": "slider_content", "label": "Slider Content", "default": "slider-content-placeholder"},
            {"type": "color", "id": "button_color", "label": "Button Background Color", "default": "#000000"},
            {"type": "color", "id": "button_text_color", "label": "Button Text Color", "default": "#ffffff"},
            {"type": "color", "id": "slider_background", "label": "Slider Background Color", "default": "#ffffff"}
          ]
        }
        {% endschema %}

        <link rel="stylesheet" href="{{ 'round-button-slider.css' | asset_url }}">

        <div class="round-button" onclick="toggleSlider()">
          {{ section.settings.button_text }}
        </div>

        <div id="sliderPanel" class="slider-panel">
          <button class="close-button" onclick="toggleSlider()">&times;</button>
          <div>
            {% if section.settings.slider_content == 'slider-content-placeholder' %}
              {% include 'slider-content' %}
            {% else %}
              {{ section.settings.slider_content }}
            {% endif %}
          </div>
        </div>

        <script src="{{ 'round-button-slider.js' | asset_url }}"></script>
        """

    def update_slider_theme(self, settings_data, rendered_html, json_output):
        self.helper.inject_script_to_theme(settings_data, rendered_html, json_output, self.activity_data["customerId"])

    def manage_slider(self):
        json_output = self.fetcher.get_related_products_user()

        print(f"json_output: {json_output}")

        # Fetch existing slider settings
        existing_settings = self.fetch_slider_settings()

        if existing_settings and "settings" in existing_settings:
            print("Slider settings:", existing_settings)
            self.update_slider_theme(existing_settings["settings"], existing_settings["renderedhtml"], json_output)
        else:
            print("No settings found, creating new slider settings...")
            # Create new slider settings
            new_settings = self.create_slider_settings()
            if new_settings:
                print("New Slider settings:", new_settings)
                self.update_slider_theme(new_settings["settings"], new_settings["renderedhtml"], json_output)

