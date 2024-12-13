from collections import Counter, defaultdict
import itertools
import json
import logging
from mlxtend.frequent_patterns import apriori, association_rules
import random
import re
from django.utils.timezone import now
from django.db.models import F

from bs4 import BeautifulSoup
from mlxtend.preprocessing import TransactionEncoder
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views import View
from jinja2 import Template
import pandas as pd
import numpy as np
import pytz
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from tabulate import tabulate
from .models import ProductOftenBoughtTogether, ProductRecommendation, ProductRelationship, UserActivity,SliderSettings
from shopifyauthenticate.models import ShopifyStore
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from datetime import datetime, timedelta
from rest_framework import status
import shopify
from django.utils.decorators import method_decorator
from smarttailor import settings

import certifi
from .serializers.recommendations import ProductRecommendationSerializer, SliderSettingsSerializer
from liquid import Liquid
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from .models import DynamicComponent
from .serializers.DynamicComponentSerializer import DynamicComponentSerializer


# Configure the logger
logging.basicConfig(
    level=logging.DEBUG,  # Set the minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Log message format
    handlers=[
        
        logging.StreamHandler()        # Output logs to the console
    ]
)

# Create a logger instance
logger = logging.getLogger("AppLogger")

@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({'csrfToken': request.COOKIES.get('csrftoken')})


@csrf_exempt
def dashboard(request):
    data = json.loads(request.body)
    shop_id = data.get("shopId")
    shop = ShopifyStore.objects.filter(id=shop_id).first()
    if hasattr(request, 'auth') and request.auth:
        
        headers = {
            'X-Shopify-Access-Token': shop.access_token
        }

        # Make the request to the Shopify API to get shop details
        response = requests.get(f'https://{shop.shop_name}/admin/api/2024-01/shop.json', headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            shop_details = response.json()
            print("Shop Details:", shop_details)
            shop_id_from_shopify = shop_details["shop"]["id"]
            shop.shop_id_from_shopify = shop_id_from_shopify
            shop.save()
            return JsonResponse({ "shop_details": shop_details, "shop":shop_details["shop"]["domain"] }, status=200)
        else:
            print(f"Failed to fetch shop details. Status code: {response.status_code}")
            return JsonResponse({ "error": "No Shop Details","shop":shop_details["shop"]["domain"] }, status=403)
    else:
        if shop:
            shop.urlsPassed = ''
            shop.save()
        return JsonResponse({'error': 'Authentication failed'}, status=403)
    



@method_decorator(csrf_exempt, name='dispatch')
class ProductRecommendationView(View):
    #TRACKING_SCRIPT_URL = "https://a01f-2409-4062-2ec7-2d5b-ed57-e47f-97ec-85b1.ngrok-free.app/static/recommendations/shopify-tracker.js"
    TRACKING_SCRIPT_URL = f"{settings.SHOPIFY_APP_URL}/static/recommendations/shopify-tracker.js"
    def post(self, request):
        """
        Handle POST requests for multiple actions like script installation, 
        fetching recommendations, or updating preferences.
        """

        data = json.loads(request.body)
        action = data.get("action")
        shop_id = data.get("shopId")
        shop = ShopifyStore.objects.filter(id=shop_id).first()

        if hasattr(request, 'auth') and request.auth:
            if action == "install_script":
                return self.install_tracking_script(request, shop)
            elif action == 'remove_script':
               return self.remove_tracking_script(request, shop)
            else:
                return JsonResponse({"error": "Invalid action specified"}, status=400)
        else:
            if shop:
                shop.urlsPassed = ''
                shop.save()
            return JsonResponse({'error': 'Authentication failed'}, status=403)
        

    def get(self, request):
        """
        Handle GET requests for actions like retrieving metrics or testing endpoints.
        """
        action = request.GET.get("action")

        if action == "get_metrics":
            return self.get_metrics(request)
        elif action == "test_endpoint":
            return JsonResponse({"message": "Test successful"})
        else:
            return JsonResponse({"error": "Invalid action specified"}, status=400)
        
    def remove_tracking_script(self, request, shop):
        """
        Remove all tracking scripts from the Shopify store except for the specified Shopify URL script.
        """
        data = json.loads(request.body)
        shop_id = data.get("shopId")

        if not shop_id:
            return JsonResponse({"error": "Missing shop URL or access token"}, status=400)

        try:
            # Shopify API session initialization
            api_version = '2024-10'  # Update this to the appropriate API version
            session = shopify.Session(f"https://{shop.shop_name}", api_version, shop.access_token)
            shopify.ShopifyResource.activate_session(session)

            # Fetch all existing scripts
            existing_scripts = shopify.ScriptTag.find()
            removed_scripts = []
            skipped_scripts = []

            # Define the script to retain
            script_to_retain = self.TRACKING_SCRIPT_URL  # Replace with your desired script's URL

            # Remove all scripts except the retained one
            for script in existing_scripts:
                if script.src != script_to_retain:
                    print(f"Removing script: {script.src}")
                    script.destroy()
                    removed_scripts.append(script.src)
                else:
                    print(f"Skipping script: {script.src}")
                    skipped_scripts.append(script.src)

            return JsonResponse({
                "success": True,
                "message": "Scripts processed successfully",
                "removed_scripts": removed_scripts,
                "skipped_scripts": skipped_scripts,
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        

    def install_tracking_script(self, request,shop):
        """
        Install the tracking script into the Shopify store.
        """

        data = json.loads(request.body)
        shop_id = data.get("shopId")
        

        if not shop_id:
            return JsonResponse({"error": "Missing shop URL or access token"}, status=400)

        # Shopify API session initialization
        try:


            api_version = '2024-10'
            session = shopify.Session(f"https://{shop.shop_name}", api_version, shop.access_token)
            shopify.ShopifyResource.activate_session(session)

            # Check if script already exists
            existing_scripts = shopify.ScriptTag.find()
            for script in existing_scripts:
                if script.src == self.TRACKING_SCRIPT_URL:
                    return JsonResponse({"success": True, "message": "Script already installed"})

            # Create a new ScriptTag
            script_tag = shopify.ScriptTag.create({
                "event": "onload",  # Load script when the page loads
                "src": self.TRACKING_SCRIPT_URL
            })

            # Handle errors
            if script_tag.errors:
                return JsonResponse({"error": script_tag.errors.full_messages()}, status=400)

            return JsonResponse({"success": True, "message": "Script installed successfully"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



@method_decorator(csrf_exempt, name='dispatch')
class TrackActivityView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract activity data from the request
        activity_data = request.data
        from .tasks import process_loggedin_user_data_1, process_loggedin_user_data_2

        if activity_data["event"] == "add_to_cart":
            process_loggedin_user_data_2.delay(request.data)
        elif activity_data["event"] == "page_view":
            process_loggedin_user_data_1.delay(request.data)
        UserActivity.objects.create(
                product_url=activity_data["url"] if "url" in activity_data else 'NA',
                user_id=activity_data["customerId"],
                product_id=activity_data["product_id"] if "product_id" in activity_data else 'NA' ,
                action_type=activity_data["action"],
            )

        return JsonResponse({"message": "Activity started tracking successfully"}, status=status.HTTP_200_OK)

class ShopifyThemeService:

    def __init__(self, shop_id, version='2024-10'):
        self.shop_id = shop_id
        self.version = version
        self.shop = ShopifyStore.objects.filter(id=shop_id).first()
        print(self.shop,shop_id)
        self.session = None
        self.main_theme = None
        self.headers = {
            'X-Shopify-Access-Token': self.shop.access_token
        }
        self.theme_id = None

    def initialize_shopify_session(self):
        """Initialize the Shopify session."""
        session = shopify.Session(self.shop.shop_name, self.version, self.shop.access_token)
        shopify.ShopifyResource.activate_session(session)

    def fetch_main_theme(self):
        """Fetch the main theme."""
        url = f'https://{self.shop.shop_name}/admin/api/{self.version}/themes.json'
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            themes = response.json().get('themes', [])
            self.main_theme = [theme for theme in themes if theme.get('role') == 'main']
            if not self.main_theme:
                raise Exception("No main theme found")
            self.theme_id = self.main_theme[0]["id"]
            print(f"Main theme ID: {self.theme_id}")
        else:
            raise Exception(f"Error fetching themes: {response.status_code}, {response.text}")

    def fetch_theme_content(self):
        """Fetch the 'theme.liquid' content."""
        url = f"https://{self.shop.shop_name}/admin/api/{self.version}/themes/{self.theme_id}/assets.json"
        params = {"asset[key]": "layout/theme.liquid"}
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            return response.json().get("asset", {}).get("value")
        else:
            raise Exception(f"Error fetching theme.liquid: {response.status_code}, {response.text}")

    def inject_script_and_update_theme(self, theme_content ):
        """Inject the script and update the theme.liquid file."""


       
        script_to_add = """
        <script>
        {% if customer %}
        window.loggedInCustomer = {
            id: "{{ customer.id }}",
            email: "{{ customer.email }}",
            first_name: "{{ customer.first_name }}",
            last_name: "{{ customer.last_name }}"
        };
        console.log("Logged in customer:", window.loggedInCustomer);
        {% else %}
        console.log("No customer is logged in.");
        window.loggedInCustomer = null;
        {% endif %}
        </script>
        """

            # Check if the script already exists
        if script_to_add.strip() in theme_content:
            print("Script already present in theme.liquid. Skipping addition.")
            return JsonResponse({"message": "Script already exists."}, status=status.HTTP_200_OK)
        updated_liquid = theme_content.replace("</body>", script_to_add + "\n</body>")
        return self.update_theme_liquid(updated_liquid)

    def update_theme_liquid(self, updated_content):
        """Update the theme.liquid file with the new content."""
        url = f"https://{settings.SHOPIFY_API_KEY}:{settings.SHOPIFY_API_SECRET}@{self.shop.shop_name}/admin/api/{self.version}/themes/{self.theme_id}/assets.json"
        payload = {
            "asset": {
                "key": "layout/theme.liquid",
                "value": updated_content
            }
        }

        response = requests.put(url, json=payload, headers=self.headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return JsonResponse({"message": "Code Installed successfully"}, status=200)



@method_decorator(csrf_exempt, name='dispatch')
class ShopifyThemeUpdater(View):

    def post(self, request):
        data = json.loads(request.body)
        shop_id = data.get("shopId")
        
        # Initialize the Shopify theme service
        theme_service = ShopifyThemeService(shop_id)

        try:
            theme_service.initialize_shopify_session()
            theme_service.fetch_main_theme()

            # Fetch the theme content and inject the script
            theme_content = theme_service.fetch_theme_content()
            return theme_service.inject_script_and_update_theme(theme_content)

        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)
        
class ProductsData(APIView):
    def get(self, request, *args, **kwargs):
        customer_name = request.query_params.get('customer', None)
        products = ProductRecommendation.objects.filter(loggedin_customer_id=customer_name)
        serializer = ProductRecommendationSerializer(products, many=True)
        shop = request.query_params.get("shop",'')
        shopMeta = ShopifyStore.objects.filter(id=shop).first()

        print(shopMeta)

        product_information = []

        for prodId in serializer.data:

            url = f"https://{shopMeta.shop_name}/admin/api/2024-10/graphql.json"
            headers = {
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": shopMeta.access_token,  # Replace with your actual access token
            }

            query = """
query GetProduct($id: ID!) {
product(id: $id) {
    id
    title
    description
    availablePublicationsCount{
    count
    }
    contextualPricing(context: {country: CA}) {
    priceRange {
    maxVariantPrice {
        amount
        currencyCode
    }
    minVariantPrice {
        amount
        currencyCode
    }
    }
}
}
}
"""

            # Define the variables for the query
            variables = {
                "id": prodId["product_id"]  
            }

            response = requests.post(
                        url,
                        headers=headers,
                        json={"query": query, "variables": variables}
                    )
            product_information.append(response.json()["data"])

        # Flatten the data
        flattened_data = []

        for item in product_information:
            # Debug: Check the type of 'product'
            if not isinstance(item, dict) or "product" not in item:
                print(f"Skipping item as it's invalid: {item}")
                continue

            product = item["product"]

            # Extract and flatten fields
            flattened_data.append({
                "id": product.get("id", ""),
                "title": product.get("title", ""),
                "description": product.get("description", ""),
                "publication_count": product.get("availablePublicationsCount", {}).get("count", 0),
                "min_price": float(product.get("contextualPricing", {}).get("priceRange", {}).get("minVariantPrice", {}).get("amount", 0)),
                "max_price": float(product.get("contextualPricing", {}).get("priceRange", {}).get("maxVariantPrice", {}).get("amount", 0)),
                "currency": product.get("contextualPricing", {}).get("priceRange", {}).get("minVariantPrice", {}).get("currencyCode", ""),
            })
        # Print the flattened data
        print(flattened_data)
        keys = flattened_data[0].keys()
        # Define defaults dynamically based on key names
        keys_dict = {
            key: (
                "Default Text" if "title" in key or "description" in key else
                0 if "count" in key or "price" in key else
                "Default Value"
            )
            for key in keys
        }

        print(keys_dict)
        return Response(keys_dict, status=status.HTTP_200_OK)

class SliderSettingsView(APIView):

    def deep_dict_compare(self,old_dict, new_dict):
        """
        Recursively compare two dictionaries and return a dictionary of changes.
        """
        changes = {}

        print(f"new_dict---------------->{new_dict}")
        if isinstance(new_dict, dict):
            # Iterate over all keys in the new dictionary
            for key, new_value in new_dict.items():
                old_value = old_dict.get(key, None)

                # If the old value doesn't exist, it means the field is new
                if old_value != new_value:
                    # If the value is a nested dictionary, recurse
                    if isinstance(new_value, dict) and isinstance(old_value, dict):
                        nested_changes = self.deep_dict_compare(old_value, new_value)
                        if nested_changes:  # Only include if there are changes
                            changes[key] = nested_changes
                    else:
                        # Otherwise, the value has changed
                        changes[key] = {'old': old_value, 'new': new_value}

            # Check if there are keys in the old dict that are missing in the new dict
            for key, old_value in old_dict.items():
                if key not in new_dict:
                    changes[key] = {'old': old_value, 'new': None}

            return changes
        return JsonResponse({"message": "Nor a dictionary"}, status=500)

    
    def post(self, request, *args, **kwargs):
        customer_name = request.data.get('customer', None)
        
        
        if not customer_name:
            return Response({"detail": "Customer name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the current SliderSettings instance
        slider_settings_instance = SliderSettings.objects.filter(customer=customer_name).first()
        print(f"slider_settings_instance------------->{slider_settings_instance}")

        if slider_settings_instance is None:
            # Create a new instance if not found
            slider_settings_instance = SliderSettings.objects.create(customer=customer_name, settings=request.data.get('settings', {}), renderedhtml=request.data.get('renderedhtml',''))
            created = True
        else:
            # Compare old settings and new settings using deep_dict_compare
            old_settings = slider_settings_instance.settings
            new_settings = request.data.get('settings', {})

            # Get the differences
            changes = self.deep_dict_compare(old_settings, new_settings)

            if changes:
                slider_settings_instance.settings = new_settings
                slider_settings_instance.save()
                print("Settings have changed:", changes)
                created = False
            else:
                print("No change in settings.")
                created = False

        serializer = SliderSettingsSerializer(slider_settings_instance)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)

    def get(self, request, *args, **kwargs):
        customer_name = request.query_params.get('customer', None)
        
        try:
            if customer_name:
                # If customer is provided, return the settings for that customer
                slider_settings = SliderSettings.objects.get(customer=customer_name)
                
                serializer = SliderSettingsSerializer(slider_settings)
              

                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # If no customer is provided, return all SliderSettings
                slider_settings = SliderSettings.objects.all()
                serializer = SliderSettingsSerializer(slider_settings, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
        
        except SliderSettings.DoesNotExist:
            if customer_name:
                return Response({"detail": "Settings not found for this customer."}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"detail": "No slider settings available."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DynamicComponentListView(APIView):
    
    def get(self, request):
        # Handle GET request to list all components
        components = DynamicComponent.objects.all()
        serializer = DynamicComponentSerializer(components, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Handle POST request to create a new component
        print(request.data)
        serializer = DynamicComponentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')    
class CaptureFrontendContentView(View):
    
    def post(self, request):
        try:
            # Parse the JSON request body
            data = json.loads(request.body)
            html_content = data.get("html", "")
            customer_name = data.get("customer", "")
            products = ProductRecommendation.objects.filter(loggedin_customer_id=customer_name)
            serializer = ProductRecommendationSerializer(products, many=True)
            shop = data.get("shop", "")
            shopMeta = ShopifyStore.objects.filter(id=shop).first()

            print(shopMeta)

            product_information = []

            for prodId in serializer.data:

                url = f"https://{shopMeta.shop_name}/admin/api/2024-10/graphql.json"
                headers = {
                    "Content-Type": "application/json",
                    "X-Shopify-Access-Token": shopMeta.access_token,  # Replace with your actual access token
                }

                query = """
    query GetProduct($id: ID!) {
    product(id: $id) {
        id
        title
        description
        availablePublicationsCount{
        count
        }
        contextualPricing(context: {country: CA}) {
        priceRange {
        maxVariantPrice {
            amount
            currencyCode
        }
        minVariantPrice {
            amount
            currencyCode
        }
        }
    }
    }
    }
    """

                # Define the variables for the query
                variables = {
                    "id": prodId["product_id"]  
                }

                response = requests.post(
                            url,
                            headers=headers,
                            json={"query": query, "variables": variables}
                        )
                product_information.append(response.json()["data"])

            # Flatten the data
            flattened_data = []

            for item in product_information:
                # Debug: Check the type of 'product'
                if not isinstance(item, dict) or "product" not in item:
                    print(f"Skipping item as it's invalid: {item}")
                    continue

                product = item["product"]

                # Extract and flatten fields
                flattened_data.append({
                    "id": product.get("id", ""),
                    "title": product.get("title", ""),
                    "description": product.get("description", ""),
                    "publication_count": product.get("availablePublicationsCount", {}).get("count", 0),
                    "min_price": float(product.get("contextualPricing", {}).get("priceRange", {}).get("minVariantPrice", {}).get("amount", 0)),
                    "max_price": float(product.get("contextualPricing", {}).get("priceRange", {}).get("maxVariantPrice", {}).get("amount", 0)),
                    "currency": product.get("contextualPricing", {}).get("priceRange", {}).get("minVariantPrice", {}).get("currencyCode", ""),
                })
          

            def populate_product_html(product):
                    return html_content.replace("Default Text", product['title'])\
                                        .replace("Default Text", product['description'] if product['description'] else 'No description available')\
                                        .replace("0", str(product['publication_count']), 1)\
                                        .replace("Default Value 0 - 0", f"{product['min_price']} - {product['max_price']} {product['currency']}")
            product_template = '<div id="products-container" style="display: flex; flex-wrap: wrap; justify-content: start;">'
            for product in flattened_data:
                product_template += populate_product_html(product)

            product_template += '</div>'

            # Now `html_content` contains the full HTML code
            print(product_template)

            # Save the HTML to a file
            with open("assests/slider-content.liquid", "w", encoding="utf-8") as f:
                f.write(product_template)

            print("HTML file generated: product_list.html")

            return JsonResponse({"message": "Content saved successfully!"}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)    

class ShopifyRenderView:
    def render_to_response(self, context):
        # Load the Liquid template content
        with open('assests/slider-content.liquid', 'r') as file:
            template_content = file.read()

        # Initialize the Liquid template engine
        liquid = Liquid(template=template_content)

        # Render the template with the context
        rendered_html = liquid.render( context)

        print(rendered_html)

   



















from faker import Faker
import random





SHOP_URL = "smarttailor324.myshopify.com"  # Replace with your store's URL

# Function to create fake customer
def create_fake_customer():
    # Retrieve the store information from the ShopifyStore model
    shop = ShopifyStore.objects.filter(shop_name="smarttailor324.myshopify.com").first()
    fake = Faker()
    if not shop:
        print(f"No Shopify store found for {SHOP_URL}")
        return
    
    # Shopify GraphQL mutation query to create a customer
    mutation = """
    mutation customerCreate($input: CustomerInput!) {
        customerCreate(input: $input) {
            userErrors {
                field
                message
            }
            customer {
                id
                email
                phone
                taxExempt
                firstName
                lastName
                amountSpent {
                    amount
                    currencyCode
                }
                smsMarketingConsent {
                    marketingState
                    marketingOptInLevel
                    consentUpdatedAt
                }
            }
        }
    }
    """

    

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": shop.access_token
    }

    # Define the customer input data with Faker
    variables = {
        "input": {
            "firstName": fake.first_name(),
            "lastName": fake.last_name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "addresses": [
                {
                    "address1": fake.street_address(),
                    "city": fake.city(),
                    "province": fake.state(),
                    "country": fake.country(),
                    "zip": fake.zipcode()
                }
            ]
        }
    }

    print(shop.shop_name)

    # Shopify GraphQL endpoint URL
    GRAPHQL_URL = f"https://{shop.shop_name}/admin/api/2024-10/graphql.json"

    # Making the POST request to Shopify's GraphQL API
    response = requests.post(GRAPHQL_URL, headers=headers, json={"query": mutation, "variables": variables})
    print(response.status_code)
 

# Function to create fake product
def create_fake_product():
    fake = Faker()
    shop = ShopifyStore.objects.filter(shop_name=SHOP_URL).first()
    mutation = """
    mutation productCreate($input: ProductInput!) {
        productCreate(input: $input) {
            product {
                id
            }
            userErrors {
                field
                message
            }
        }
    }
    """

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": shop.access_token
    }

    # Define fake product input data
    variables = {
        "input": {
            "title": fake.word().capitalize(),  # Random product title
            "productType": fake.word().capitalize(),  # Random product type
            "vendor": fake.company()  # Random vendor name
        }
    }


    # Headers including the authorization token
    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': shop.access_token
    }
    GRAPHQL_URL = f"https://{SHOP_URL}/admin/api/2024-10/graphql.json"
    # Making the POST request to Shopify's GraphQL API
    response = requests.post(GRAPHQL_URL, headers=headers, json={"query": mutation, "variables": variables})
    print("products", response.status_code)

# Function to create fake order
def create_fake_order(customer_id, product_id,amount):
    fake = Faker()
    # GraphQL mutation query
    # GraphQL Mutation
    mutation = """
mutation OrderCreate($order: OrderCreateOrderInput!, $options: OrderCreateOptionsInput) {
  orderCreate(order: $order, options: $options) {
    userErrors {
      field
      message
    }
    order {
      id
      displayFinancialStatus
      shippingAddress {
        lastName
        address1
        city
        provinceCode
        countryCode
        zip
      }
      billingAddress {
        lastName
        address1
        city
        provinceCode
        countryCode
        zip
      }
      customer {
        id
      }
    }
  }
}
"""

    variables = {
    "order": {
        "lineItems": [
            {
                "variantId": product_id,
                "quantity": random.randint(1, 10)
            }
        ],
        "customerId": customer_id,
        "transactions":{
           "amountSet":{
               "shopMoney":{
                   "amount": amount,
                   "currencyCode":fake.currency_code()
               }
           }
        },
        "financialStatus": "PENDING",
        "shippingAddress": {
            "lastName": fake.word(),
            "address1": "123 Main St",
            "city": "Ottawa",
            "countryCode": "CA",
            "provinceCode": "ON",
            "zip": "K1P 1J1"
        },
        "billingAddress": {
            "lastName": fake.word(),
            "address1": "321 Secondary St",
            "city": "Ottawa",
            "countryCode": "CA",
            "provinceCode": "ON",
            "zip": "K1P 1J1"
        }
    }
}

  
    GRAPHQL_URL = f"https://{SHOP_URL}/admin/api/2024-10/graphql.json"
    shop = ShopifyStore.objects.filter(shop_name=SHOP_URL).first()

    headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": shop.access_token
        }

    # Making the POST request to Shopify's GraphQL API
    response = requests.post(GRAPHQL_URL, headers=headers, json={"query": mutation, "variables": variables})
    print("orders", response.status_code)

# Django view to generate fake data
@csrf_exempt  # Disable CSRF validation for the sake of testing (ensure security in production)
def generate_fake_data(request):
    if request.method == "POST":
            
            data_ordered = []

            # grouped_data = {"pids": [], "varIds": [], "cids": []}
            
            def fetch_products():
                query = """
                query {
                products(first: 10, reverse: true) {
                    edges {
                    node {
                        id
                        title
                        variants(first:5){
                          nodes{
                          id
                          price
                          
                          }
                        
                        }
                        }
                    }
                    }
                }
                

                """
                
                SHOP_URL = "smarttailor324.myshopify.com"  

                GRAPHQL_URL = f"https://{SHOP_URL}/admin/api/2024-10/graphql.json"
                shop = ShopifyStore.objects.filter(shop_name=SHOP_URL).first()

                headers = {
                    "Content-Type": "application/json",
                    "X-Shopify-Access-Token": shop.access_token,
                }

                response = requests.post(GRAPHQL_URL, headers=headers, json={"query": query})
                
                if response.status_code == 200:
                    data = response.json()
                    if "errors" in data:
                        print("Errors:", data["errors"])
                    else:
                        products = data["data"]["products"]["edges"]
                        for product in products:
                            temp = {}
                            nodeVariants = product["node"]["variants"]["nodes"]
                            for var in nodeVariants:
                                temp["pid"]=product["node"]["id"]
                                temp["varIds"]=var["id"]
                                temp["price"]=var["price"]
                               
                                query = """
                                                query {
                                    customers(first: 10) {
                                        edges {
                                        node {
                                            id
                                        }
                                        }
                                    }
                                    }

                                  """
                
                                SHOP_URL = "smarttailor324.myshopify.com"  

                                GRAPHQL_URL = f"https://{SHOP_URL}/admin/api/2024-10/graphql.json"
                                shop = ShopifyStore.objects.filter(shop_name=SHOP_URL).first()

                                headers = {
                                    "Content-Type": "application/json",
                                    "X-Shopify-Access-Token": shop.access_token,
                                }

                                response = requests.post(GRAPHQL_URL, headers=headers, json={"query": query})
                                if response.status_code == 200:
                                    data = response.json()
                                    if "errors" in data:
                                        print("Errors:", data["errors"])
                                    else:
                                        customers = data["data"]["customers"]["edges"]
                                        for c in customers:
                                            temp["cid"] = c["node"]["id"]
                                            data_ordered.append(temp)
                                            
                                            
                                else:
                                    print(f"Error: {response.status_code} - {response.text}")

                                    
                            
                else:
                    print(f"Error: {response.status_code} - {response.text}")
            # Call the function
            fetch_products()

            
            # Call the function
            
            
            

            # Step 1: Filter the data to include only entries with `varIds` and `price`
            filtered_data = [entry for entry in data_ordered if 'varIds' in entry and 'price' in entry]

            # Step 2: Shuffle the filtered data
            random.shuffle(filtered_data)

            # The filtered and shuffled data
           

            # Group data by pid, varId, and cid

                        # Example usage
            

            # Function to create orders from the filtered data
            def create_orders(filtered_data, num_orders):
                # Filter only valid products and customers

                
                
                # Create the specified number of orders
                for _ in range(num_orders):
                    logger.debug(f"data_ordered--------->{filtered_data}")
                    for cc in filtered_data:
                        # Extract customer_id, product_id, and amount (price)
                        customer_id = cc["cid"]
                        product_id = cc["varIds"]
                        amount = cc["price"]
        

                        logger.debug(f"customer_id, product_id, amount,displayName----> {customer_id}, {product_id} , {amount}")
                        create_fake_order(customer_id, product_id, amount)
    

                    

                    

                #     # Create and append the order
                #     # create_fake_order(customer_id, product_id, amount,displayName)


            create_orders(filtered_data, 40)
            
            return JsonResponse({
                    "customers_created": "jj",
                    # "products_created": [product["id"] for product in products],
                    # "orders_created": orders
                })
        
        

    else:
        return JsonResponse({"error": "Invalid HTTP method. Use POST."}, status=405)
    