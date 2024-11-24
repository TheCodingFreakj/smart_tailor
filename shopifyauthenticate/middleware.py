import json
from urllib.parse import urlparse, parse_qs
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from datetime import datetime, timedelta
from .models import ShopifyStore
from django.utils.timezone import make_aware
class ShopifyAuthMiddleware(MiddlewareMixin):
    
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        print("Executing before the view.")
        # Access the view function and its arguments
        print(f"View Function: {view_func.__name__}")
        print(f"View Args: {view_args}")
        print(f"View KWArgs: {view_kwargs}")
        

        print("refreer------------------------------------------------>", request.META.get('HTTP_REFERER', ''))
   
                # Capture and parse the body if it exists
        if request.method in ['GET', 'POST', 'PUT', 'PATCH']:
            try:
                # Decode and parse the request body as JSON
                body_data = json.loads(request.body.decode('utf-8'))
                print(f"Request Body: {body_data}")
                shop_id = body_data.get("shopId")
                shop = ShopifyStore.objects.filter(id=shop_id).first()

                referer = request.META.get('HTTP_REFERER', '')

                if request.META.get('HTTP_REFERER', '') == 'https://admin.shopify.com/':
                     ShopifyStore.objects.filter(id=shop_id).update(
                    urlsPassed='https://admin.shopify.com/',
                    is_installed="installed"
                 )
                     
                else:

                    ShopifyStore.objects.filter(id=shop_id).update(
                    urlsPassed=shop.urlsPassed + referer,
                    is_installed="installed"
                 )
                 

                if len(shop.urlsPassed.split(",")) > 1 and 'https://admin.shopify.com/' in shop.urlsPassed.split(","):
                    request.auth = True
                else:
                    request.auth = False       
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error decoding request body: {e}")

                if shop:
                    shop.urlsPassed = ''
                    shop.save()


    def process_response(self, request, response):
        print("Executing after the view.")
        
        # Check if the response is a JsonResponse
        if isinstance(response, JsonResponse):
            # Extract the JSON data from the response
            response_data = json.loads(response.content)  # This will give you the dictionary
            
            # Check if 'shop' attribute exists in the response
            shop = response_data.get('shop')
            if shop:
                # You can now use the 'shop' data to update the database or perform other actions
                print(f"Shop data from response: {shop}")
                
                # Example: You can update the database here if needed
                shop_instance = ShopifyStore.objects.filter(shop_name=shop.shop_name).first()
                if shop_instance:
                    shop_instance.urlsPassed = ''
                    shop_instance.save()

        # Optionally, modify the response if needed before returning
        return response
