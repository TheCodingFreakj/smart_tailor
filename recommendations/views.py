import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views import View
import requests
from .models import UserActivity
from shopifyauthenticate.models import ShopifyStore
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from datetime import datetime, timedelta
from rest_framework import status
import shopify
from django.utils.decorators import method_decorator

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
    



@method_decorator(csrf_exempt, name='dispatch')
class ProductRecommendationView(View):
    TRACKING_SCRIPT_URL = "https://smart-tailor.onrender.com/static/recommendations/shopify-tracker.js"
    
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
            api_version = '2024-07'  # Update this to the appropriate API version
            session = shopify.Session(f"https://{shop.shop_name}", api_version, shop.access_token)
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

@method_decorator(csrf_exempt, name='dispatch')
class TrackActivityView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract activity data from the request
        activity_data = request.data
        

        if activity_data:
            shop_name = activity_data["shop"]
            customerId = activity_data["customerId"]
            shop = ShopifyStore.objects.filter(shop_name=shop_name).first()

            UserActivity.objects.create(
                product_url=activity_data["url"] if "url" in activity_data else None
                user_id=customerId,
                product_id=activity_data["product_id"] if "product_id" in activity_data else None ,
                action_type=activity_data["action"],
            )

            if activity_data.action == "show_related_viewed_product_based_on_user":
                self.get_related_products_user(customerId, shop)
            elif(activity_data.action == "show_related_product_based_on_category"):
                self.fetch_shopify_product_category(activity_data["product_id"], shop)
            
            print("Received activity data:", request.data)

            # Respond with a success message
            return JsonResponse({"message": "Activity tracked successfully"}, status=status.HTTP_200_OK)


    def fetch_shopify_product_category(self,product_id, shop):
        url = f"https://{shop.shop_name}/admin/api/2024-01/products/{product_id}.json"
        headers = {"X-Shopify-Access-Token": shop.access_token}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None

    def get_related_products_user(self,customer_id,shop):
        # feed to ML for deeper insights
        pass
