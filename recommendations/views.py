import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views import View
import requests
from shopifyauthenticate.models import ShopifyStore
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from datetime import datetime, timedelta
from rest_framework import status


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
            return JsonResponse({ "shop_details": shop_details, "shop":shop_details["shop"]["domain"] }, status=200)
        else:
            print(f"Failed to fetch shop details. Status code: {response.status_code}")
            return JsonResponse({ "error": "No Shop Details","shop":shop_details["shop"]["domain"] }, status=403)
    else:
        if shop:
            shop.urlsPassed = ''
            shop.save()
        return JsonResponse({'error': 'Authentication failed'}, status=403)
    




class ProductRecommendationView(View):
    TRACKING_SCRIPT_URL = "https://smart-tailor.onrender.com/static/shopify-tracker.js"
    @csrf_exempt
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
            elif action == "fetch_recommendations":
                return self.fetch_recommendations(request, shop)
            elif action == "update_preferences":
                return self.update_preferences(request, shop)
            elif action == 'remove_script':
               return self.remove_tracking_script(request, shop)
            else:
                return JsonResponse({"error": "Invalid action specified"}, status=400)
        else:
            if shop:
                shop.urlsPassed = ''
                shop.save()
            return JsonResponse({'error': 'Authentication failed'}, status=403)
        
    @csrf_exempt
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
    @csrf_exempt    
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
            shop_url = f"{shop_id}.myshopify.com"
            api_version = '2024-07'  # Update this to the appropriate API version
            session = shopify.Session(f"https://{shop_url}", api_version, shop.access_token)
            shopify.ShopifyResource.activate_session(session)

            # Fetch all existing scripts
            existing_scripts = shopify.ScriptTag.find()
            script_to_remove = None

            # Find the script we added earlier
            for script in existing_scripts:
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
        
    @csrf_exempt
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

            api_version = '2024-07'
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
    # def fetch_recommendations(self, request):
    #     """
    #     Fetch product recommendations for a customer.
    #     """
    #     shop_url = request.POST.get("shop")
    #     customer_id = request.POST.get("customer_id")

    #     if not shop_url or not customer_id:
    #         return JsonResponse({"error": "Missing shop URL or customer ID"}, status=400)

    #     # Placeholder for recommendation logic
    #     recommendations = [
    #         {"product_id": 101, "name": "Product A"},
    #         {"product_id": 102, "name": "Product B"}
    #     ]
    #     return JsonResponse({"recommendations": recommendations})

    # def update_preferences(self, request):
    #     """
    #     Update store preferences for product recommendations.
    #     """
    #     shop_url = request.POST.get("shop")
    #     preferences = request.POST.get("preferences")

    #     if not shop_url or not preferences:
    #         return JsonResponse({"error": "Missing shop URL or preferences"}, status=400)

    #     # Save preferences to the database (placeholder logic)
    #     return JsonResponse({"success": "Preferences updated"})

    # def get_metrics(self, request):
    #     """
    #     Retrieve metrics or analytics related to recommendations.
    #     """
    #     shop_url = request.GET.get("shop")

    #     if not shop_url:
    #         return JsonResponse({"error": "Missing shop URL"}, status=400)

    #     # Placeholder metrics
    #     metrics = {
    #         "conversion_rate": 5.2,
    #         "average_order_value": 120.5,
    #         "top_products": [
    #             {"product_id": 101, "name": "Product A"},
    #             {"product_id": 102, "name": "Product B"}
    #         ]
    #     }
    #     return JsonResponse({"metrics": metrics})

from rest_framework.views import APIView    
class TrackActivityView(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        # Extract activity data from the request
        activity_data = request.data
        
        # You can now process this data (store in DB, analyze, etc.)
        # Example of logging activity to the console (you can replace this with actual processing logic)
        print("Received activity data:", activity_data)

        # Respond with a success message
        return JsonResponse({"message": "Activity tracked successfully"}, status=status.HTTP_200_OK)