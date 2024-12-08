from collections import Counter, defaultdict
import itertools
import json
import logging
import os
import random
import re
from django.core import serializers
from bs4 import BeautifulSoup
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
from .models import ProductRecommendation, ProductRelationship, UserActivity,SliderSettings
from shopifyauthenticate.models import ShopifyStore
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from datetime import datetime, timedelta
from rest_framework import status
import shopify
from django.utils.decorators import method_decorator
from smarttailor import settings
from sklearn.metrics.pairwise import cosine_similarity
import certifi
from .serializers.recommendations import ProductRecommendationSerializer, SliderSettingsSerializer



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
    #TRACKING_SCRIPT_URL = "https://b6da-2409-4062-4d8b-b24-8d86-a79f-873b-26e8.ngrok-free.app/static/recommendations/shopify-tracker.js"
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
        Remove the tracking script from the Shopify store.
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
            script_to_remove = None

            # Find the script we added earlier
            for script in existing_scripts:
                print(script.src)
                if script.src == self.TRACKING_SCRIPT_URL:  # Replace with your script's URL
                    script_to_remove = script
                    break

            # If the script was found, remove it
            if script_to_remove:
                script_to_remove.destroy()
                return JsonResponse({"success": True, "message": "Script removed successfully"})
            else:
                return JsonResponse({"error": "Script not found"}, status=404)

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



class ShopifyDataFetcher:
    def __init__(self, shop, version, activity_data):
        self.shop = shop
        self.version = version
        self.activity_data = activity_data
        self.base_url = f"https://{shop.shop_name}/admin/api/{version}/graphql.json"
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": shop.access_token
        }

    def execute_graphql_query(self, query, variables=None):
        """Helper function to make the GraphQL API request."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        response = requests.post(self.base_url, headers=self.headers, data=json.dumps(payload), verify=certifi.where())
        
        if response.status_code != 200:
            logger.error(f"GraphQL request failed with status code {response.status_code}")
            return None
        
        return response.json()

    def get_all_customers(self):
        """Fetch all enabled customers."""
        query = """
        {
            customers(first: 10) {
                edges {
                    node {
                        id
                        state
                    }
                }
            }
        }
        """
        customer_data = self.execute_graphql_query(query)
        if not customer_data:
            return []

        # Extract numeric customer IDs
        customers = [edge['node'] for edge in customer_data['data']['customers']['edges']]
        numeric_ids = [re.search(r'\d+', customer['id']).group() for customer in customers]
        return numeric_ids

    def get_customer_orders(self, customer_ids):
        """Fetch all orders related to the given customer IDs."""
        all_customer_interactions = []
        
        for customer_id in customer_ids:
            query = f"""
            {{
                orders(first: 10, query: "customer_id:{customer_id}") {{
                    edges {{
                        node {{
                            id
                            updatedAt
                            customer {{
                                id
                            }}
                            customerJourney {{
                                customerOrderIndex
                                daysToConversion
                                firstVisit {{
                                    source
                                }}
                                moments {{
                                    occurredAt
                                }}
                                lastVisit {{
                                    source
                                }}
                            }}
                            lineItems(first:5) {{
                                edges {{
                                    node {{
                                        name
                                        quantity
                                        product {{
                                            id
                                            category {{
                                                name
                                            }}
                                            title
                                            variants(first: 5) {{
                                                nodes {{
                                                    displayName
                                                    price
                                                }}
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
            """
            customer_interaction_data = self.execute_graphql_query(query)
            if customer_interaction_data:
                all_customer_interactions.append(customer_interaction_data)
        
        return all_customer_interactions

    def get_all_products(self):
        """Fetch all products in the store."""
        query = """
        query {
            products(first: 10, reverse: true) {
                edges {
                    node {
                        id
                        title
                    }
                }
            }
        }
        """
        product_data = self.execute_graphql_query(query)
        if not product_data:
            return []
        
        return [product['node']['title'] for product in product_data['data']['products']['edges']]

    def process_customer_data(self, customer_interactions):
        """Process and normalize customer interaction data."""
        customer_data = []

        for data in customer_interactions:
            orders = data.get("data", {}).get("orders", {}).get("edges", [])
            for order in orders:
                node = order.get("node", {})
                customer_journey = node.get("customerJourney") if node.get("customerJourney") is not None else {}

                # Safely extract customerJourney fields with additional None checks
                order_index = customer_journey.get("customerOrderIndex") if customer_journey else None
                days_to_conversion = customer_journey.get("daysToConversion") if customer_journey else None
                first_visit_source = (
                    customer_journey.get("firstVisit", {}).get("source") if customer_journey and customer_journey.get("firstVisit") else None
                )
                last_visit_source = (
                    customer_journey.get("lastVisit", {}).get("source") if customer_journey and customer_journey.get("lastVisit") else None
                )
                moments = (
                    [
                        {"occurredAt": moment.get("occurredAt")}
                        for moment in customer_journey.get("moments", [])
                    ]
                    if customer_journey and customer_journey.get("moments")
                    else []
                )

                line_items = node.get("lineItems", {}).get("edges", [])

                for item in line_items:
                    product_data = item.get("node", {})
                    product = product_data.get("product", {})
                    variants = product.get("variants", {}).get("nodes", [])
                    
                    customer_data.append({
                         "customer_id": node.get("customer", {}).get("id"),
                        "product_id": product["id"],
                        "logged_in_customer": self.activity_data["customerId"],
                        "product_name": product_data.get("name", "Unknown Product"),
                        "quantity": product_data.get("quantity") if product.get("quantity") else None,
                        "category": product["category"]["name"] if product.get("category") and "name" in product["category"] else None,
                        "variants": [
                            {"displayName": variant.get("displayName"), "price": variant.get("price")}
                            for variant in variants
                        ],
                        "order_index": order_index,
                        "days_to_conversion": days_to_conversion,
                        "first_visit_source": first_visit_source,
                        "last_visit_source": last_visit_source,
                        "moments": moments,
                        "order_updated_at": node.get("updatedAt"),
                    })
        return customer_data

    def analyze_data(self, customer_data):
        """Analyze the customer data to calculate relevant metrics."""
        df = pd.json_normalize(customer_data, record_path=['moments'], meta=[
            'customer_id', 'logged_in_customer', 'product_name', 'product_id', 'quantity', 
            'category', 'variants', 'order_index', 'days_to_conversion', 'first_visit_source', 
            'last_visit_source', 'order_updated_at'
        ])

        # Convert 'occurredAt' to datetime and handle empty variants
        df['occurredAt'] = pd.to_datetime(df['occurredAt'])
        df['product_price'] = df['variants'].apply(lambda x: float(x[0]['price']) if x else None)
        df['product_displayName'] = df['variants'].apply(lambda x: x[0]['displayName'] if x else None)

        now_utc = datetime.now(pytz.utc)
        df['days_since_last_purchase'] = (now_utc - df['occurredAt']).dt.days
        df['quantity'] = df['quantity'].apply(lambda x: x if x is not None else 1)

        # Total quantity purchased per product
        product_purchase_quantity = df.groupby('product_name')['quantity'].sum()

        # Total revenue per product
        df['total_revenue'] = df["quantity"] * df['product_price']
        product_revenue = df.groupby('product_name')['total_revenue'].sum()

        # Total spend per customer
        df['total_spent'] = df['quantity'] * df['product_price']
        customer_total_spent = df.groupby('customer_id')['total_spent'].sum()

        # Sort by total spend to find high-value customers
        high_value_customers = customer_total_spent.sort_values(ascending=False)

        # Log analysis results
        logger.debug(f"High-value customers: {high_value_customers}")
        logger.debug(f"Product purchase quantities: {product_purchase_quantity}")
        logger.debug(f"Product revenue: {product_revenue}")

        return high_value_customers, product_purchase_quantity, product_revenue, df

    def get_related_products_user(self):
        """Main function to fetch data and analyze customer interactions."""
        customer_ids = self.get_all_customers()
        all_customer_interactions = self.get_customer_orders(customer_ids)
        customer_data = self.process_customer_data(all_customer_interactions)
        high_value_customers, product_purchase_quantity, product_revenue,df = self.analyze_data(customer_data)
        self.recommend_products_based_on_similarity(df, high_value_customers)
        
        
    
    def recommend_products_based_on_similarity(self,df, high_value_customers):
        """
        Function to recommend products based on the cosine similarity of customers' purchasing behavior.
        """
        # Create a pivot table with customers as rows and products as columns
        pivot_table = df.pivot_table(index='customer_id', columns='product_name', values='quantity', aggfunc='sum', fill_value=0)

        # Calculate cosine similarity between customers
        cosine_sim = cosine_similarity(pivot_table)

        # Example: Find most similar customers to the first high-value customer
        target_customer_idx = 0  # Use the top high-value customer as target
        similar_customers = cosine_sim[target_customer_idx]

        # Create a DataFrame with similarity scores and customer IDs
        similarity_df = pd.DataFrame({
            'customer_id': pivot_table.index,
            'similarity_score': similar_customers
        })

        # Exclude self-similarity (1.0 score)
        similarity_df = similarity_df[similarity_df['customer_id'] != pivot_table.index[target_customer_idx]]

        # Sort by similarity score (descending)
        similarity_df_sorted = similarity_df.sort_values(by='similarity_score', ascending=False)

        # Display the top N similar customers (e.g., top 5)
        top_similar_customers = similarity_df_sorted.head(5)
        logger.debug(f"Top similar customers: {top_similar_customers}")

        # Get products purchased by these similar customers
        similar_customers_ids = top_similar_customers['customer_id'].tolist()
        recommended_products = df[df['customer_id'].isin(similar_customers_ids)]

        # Recommend top N products (e.g., most purchased)
        recommended_products = recommended_products.groupby('product_name').agg(
            product_id=('product_id', 'first'),
            quantity=('quantity', 'sum'),
            customer_id=('customer_id', 'first'),
            loggedin_customer=('logged_in_customer', 'first')
        ).sort_values('quantity', ascending=False)

        logger.debug(f"Recommended products: {recommended_products.head()}")

        # Extract top recommended product names
        product_names = recommended_products.head().index.tolist()

        # Assuming 'recommended_products' is your DataFrame
        recommended_products = pd.DataFrame(recommended_products.head(), index=product_names)

        # Store recommendations to the database (this would depend on your model logic)
        self.store_recommendations_from_df(recommended_products)

        # Retrieve recommendations from the database for the logged-in customer
        recommendations = ProductRecommendation.objects.filter(
            loggedin_customer_id=self.activity_data["customerId"]
        ).order_by('-recommendation_score')

        # Serialize the queryset
        recommendations_json = serializers.serialize('json', recommendations)

        # This is the JSON you can pass to the frontend
        logger.debug(f"Serialized recommendations: {recommendations_json}")

        # Parse the serialized JSON and extract relevant data
        extracted_data = []
        for entry in json.loads(recommendations_json):  # Parse the JSON string to Python objects
            if 'fields' in entry:
                fields = entry['fields']
                extracted_data.append({
                    "product_id": fields["product_id"],
                    "recommendation_score": fields["recommendation_score"],
                    "timestamp": fields["timestamp"],
                    "last_updated": fields["last_updated"],
                    "product_name": fields["product_name"],
                    "customer_id": fields["customer_id"],
                    "loggedin_customer_id": fields["loggedin_customer_id"]
                })
            else:
                logger.warning(f"Invalid entry format: {entry}")

        # Convert the extracted data to JSON
        json_output = extracted_data
        logger.debug(f"Extracted recommendation data: {json_output}")

        return json_output
    def store_recommendations_from_df(self,df):
        """
        Processes the DataFrame and stores or updates product recommendations in the database.
        
        :param df: A pandas DataFrame containing product recommendation data
        """
        for product_name,  row in df.iterrows():
            product_id = row['product_id']
            recommendation_score = row['quantity']
            customer_id = row['customer_id']
            loggedin_customer_id = row['loggedin_customer']
            
            
            try:
                # Try to get the existing recommendation
                recommendation = ProductRecommendation.objects.get(product_id=product_id)
                # Update the recommendation score if it exists
                recommendation.recommendation_score = recommendation_score
                recommendation.customer_id = customer_id
                recommendation.loggedin_customer_id = loggedin_customer_id
                recommendation.product_name = product_name  # Optionally update the product name
                recommendation.save()
                print(f"Updated recommendation for {product_name} ({product_id}) with score {recommendation_score}")
            except ProductRecommendation.DoesNotExist:
                # If the recommendation doesn't exist, create a new record
                recommendation = ProductRecommendation.objects.create(
                    product_id=product_id,
                    product_name=product_name,
                    recommendation_score=recommendation_score,
                    customer_id=customer_id,
                    loggedin_customer_id = loggedin_customer_id
                )
                print(f"Created new recommendation for {product_name} ({product_id}) with score {recommendation_score}")




@method_decorator(csrf_exempt, name='dispatch')
class TrackActivityView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract activity data from the request
        activity_data = request.data
        
        # self.upload_app_block_to_theme(shop,'2024-10')
        print("Checkin")
        

        
        print("Received activity data:", request.data)

        if activity_data:
            shop_name = activity_data["shop"]
            customerId = activity_data["customerId"] or 1

            shop = ShopifyStore.objects.filter(shop_name=shop_name).first()
            api_version = '2024-10'
            self.install_customer_tracking_script(shop.shop_name, shop.access_token)
            # 2024-10
            
            

            UserActivity.objects.create(
                product_url=activity_data["url"] if "url" in activity_data else 'NA',
                user_id=customerId,
                product_id=activity_data["product_id"] if "product_id" in activity_data else 'NA' ,
                action_type=activity_data["action"],
            )

            if activity_data["action"] == "show_related_viewed_product_based_on_user":
                self.get_related_products_user(activity_data, shop,api_version)
            elif(activity_data["action"] == "show_related_product_based_on_often_bought"):
                self.fetch_often_bought_together(activity_data, shop,api_version)
        return JsonResponse({"message": "Activity tracked successfully"}, status=status.HTTP_200_OK)


    def fetch_often_bought_together(self,activity_data, shop,api_version):
        params = {
            "customer_id": activity_data["customerId"]
        }
        url = f"https://{shop.shop_name}/admin/api/{api_version}/orders.json"
        headers = {
            "X-Shopify-Access-Token": shop.access_token,
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers, params=params)


        # Step 1: Extract product details
        order_products = []
        for order in response.json()["orders"]:
            order_number = order["order_number"]
            products = [
                {"product_id": item["product_id"], "quantity": item["quantity"]}
                for item in order["line_items"]
            ]
            order_products.append({"order_number": order_number, "products": products})

        # Step 2: Generate product pairs
        pair_counts = Counter()
        for products in order_products:
            # Generate all unique pairs within an order
            pairs = itertools.combinations(sorted(products), 2)
            pair_counts.update(pairs)

        # Step 3: Output frequently bought together pairs
        frequent_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)

        print("Frequently Bought Together:")
        for pair, count in frequent_pairs:
            print(f"{pair[0]} and {pair[1]} were bought together {count} times.")

        # Step 4: Generate recommendations for bundles
        bundle_suggestions = defaultdict(list)
        for (product_a, product_b), count in frequent_pairs:
            bundle_suggestions[product_a].append((product_b, count))

        print("\nSuggested Bundles:")
        for product, suggestions in bundle_suggestions.items():
            print(f"For {product}:")
            for suggestion, count in suggestions:
                print(f"  - {suggestion} (bought together {count} times)")
        
    def get_related_products_user(self,activity_data,shop,version):

        json_output = ShopifyDataFetcher(shop,version,activity_data).get_related_products_user()
    
        # Print the result
        print(f"json_output.................>{json_output}")
        helper = ShopifyThemeHelper(shop)

        print("helper...........................................")

        url = f"{settings.SHOPIFY_APP_URL}/slider-settings/"  # Adjust the URL as per your API
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": shop.access_token
        }


        response = requests.get(url, headers=headers)

        # Check if the response is successful
        if response.status_code == 200:
            # Parse the JSON response
            settings_data = response.json()
            print("Slider settings:", settings_data)
        else:
            print(f"Failed to fetch settings. Status code: {response.status_code}")
            print("Error:", response.text)
        # create with default settings

        configData = {
  "name": "Round Button with Slider",
  "settings": [
    {
      "type": "text",
      "id": "button_text",
      "label": "Button Text",
      "default": "Open Slider"
    },
    {
      "type": "textarea",
      "id": "slider_content",
      "label": "Slider Content",
      "default": "Add your slider content here."
    },
    {
      "type": "color",
      "id": "button_color",
      "label": "Button Background Color",
      "default": "#000000"
    },
    {
      "type": "color",
      "id": "button_text_color",
      "label": "Button Text Color",
      "default": "#ffffff"
    },
    {
      "type": "color",
      "id": "slider_background",
      "label": "Slider Background Color",
      "default": "#ffffff"
    }
  ]
}



        app_url = f"{settings.SHOPIFY_APP_URL}/slider-settings/"
        params = {"customer": activity_data["customerId"]}
        responsesettings = requests.get(app_url,params=params)
        print(responsesettings.json())
        config_data_json = None

        if "settings" in  responsesettings.json():

            config_data_json = responsesettings.json()["settings"]
            helper.inject_script_to_theme(config_data_json, responsesettings.json()["renderedhtml"],json_output,activity_data["customerId"])
        else:
            #create an object
            app_url = f"{settings.SHOPIFY_APP_URL}/slider-settings/"
            payloadFor={
                "customer": activity_data["customerId"],
                "settings": configData,
               "renderedhtml": """
{% schema %}
{
  "name": "Round Button with Slider",
  "settings": [
    {
      "type": "text",
      "id": "button_text",
      "label": "Button Text",
      "default": "Open Slider"
    },
    {
      "type": "textarea",
      "id": "slider_content",
      "label": "Slider Content",
      "default": "slider-content-placeholder"
    },
    {
      "type": "color",
      "id": "button_color",
      "label": "Button Background Color",
      "default": "#000000"
    },
    {
      "type": "color",
      "id": "button_text_color",
      "label": "Button Text Color",
      "default": "#ffffff"
    },
    {
      "type": "color",
      "id": "slider_background",
      "label": "Slider Background Color",
      "default": "#ffffff"
    }
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
    <!-- Dynamically render slider content -->
    {% if section.settings.slider_content == 'slider-content-placeholder' %}
      {% include 'slider-content' %}
    {% else %}
      {{ section.settings.slider_content }}
    {% endif %}
  </div>
</div>

<script src="{{ 'round-button-slider.js' | asset_url }}"></script>
"""

            }
            responsesettings = requests.post(app_url,json=payloadFor)
            print(responsesettings.json())
            helper.inject_script_to_theme(responsesettings.json()["settings"], responsesettings.json()["renderedhtml"], json_output,activity_data["customerId"])
        self.fetch_often_bought_together(activity_data, shop,version)
    
    def install_customer_tracking_script(self,shop,access_token):
        """
        Install the tracking script into the Shopify store.
        """
        api_version = '2024-10'
        # The URL to compare against
        target_url = f"{settings.SHOPIFY_APP_URL}/static/recommendations/shopify-tracker.js"
        endpoint = f"https://{shop}/admin/api/2024-10/script_tags.json"

        payload = {
        "script_tag": {
            "event": "onload",
            "src": f"{settings.SHOPIFY_APP_URL}/static/recommendations/customer-tracking.js"
        }
        }

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token
        }


        response = requests.get(endpoint, headers=headers)
        script_tags = response.json().get('script_tags', [])

        print(script_tags)


        for script_tag in script_tags:
            script_url = script_tag.get('src')
            
            # Check if the URL is not equal to the target URL
            if script_url != target_url:
                script_id = script_tag['id']
                delete_endpoint = f"https://{shop}/admin/api/2024-10/script_tags/{script_id}.json"
                
                delete_response = requests.delete(delete_endpoint, headers=headers)
                if delete_response.status_code == 200:
                    print(f"Deleted script tag with ID: {script_id}")
                else:
                    print(f"Failed to delete script tag with ID: {script_id}, Response: {delete_response.json()}")
            else:
                print(f"Skipping deletion of script tag with ID: {script_tag['id']} (URL matches the target URL)")

        
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

# views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from .models import DynamicComponent
from .serializers.DynamicComponentSerializer import DynamicComponentSerializer

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
from liquid import Liquid

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

   
