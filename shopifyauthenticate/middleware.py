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
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                # Decode and parse the request body as JSON
                body_data = json.loads(request.body.decode('utf-8'))
                print(f"Request Body: {body_data}")
                shop_id = body_data.get("shopId")
                shop = ShopifyStore.objects.filter(id=shop_id).first()


                if request.path in shop.urlsPassed.split(","):
                    updated_urls = ','.join(url.strip() for url in shop.urlsPassed.split(',') if url.strip() != request.path) + f', {request.path}'
                else:
                    # Add the new path if '/shopify/callback' is not found
                    updated_urls = shop.urlsPassed + "," + request.path

                ShopifyStore.objects.filter(shop_name=request.GET.get('shop')).update(
                    urlsPassed=updated_urls,
                    is_installed="installed"
                )

                if shop.urlsPassed.split(",")[1] == 'https://admin.shopify.com/':
                    request.auth = True
                else:
                    request.auth = False       
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error decoding request body: {e}")
 

    
        if request.path == '/shopify/callback/':
            code = request.GET.get('code')
            request.code = code     
        if request.path == '/shopify/install/':
                full_url = request.build_absolute_uri()
                parsed_url = urlparse(full_url)
                query_params = parse_qs(parsed_url.query)
                hmac_value = query_params.get('hmac', [None])[0]
                hmac_received = request.GET.get('hmac')
                shopify_hmac = hmac_received if hmac_received else hmac_value
                ShopifyStore.objects.update_or_create(
                    shop_name=request.GET.get('shop'),  # Use the shop name as the unique identifier
                    defaults={'current_hmac': shopify_hmac, "canAsk":True}  # Update the access token
                )
                print(f"hmac_received----------->{hmac_received}")  
                print(f"hmac_value----------->{hmac_value}")

    def process_response(self, request, response):
        print("Executing after the view.")
        
        # Check if the response is a JsonResponse
        if isinstance(response, JsonResponse):
            # Extract the JSON data from the response
            response_data = response.json()  # This will give you the dictionary
            
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
    

# class ShopifyHMACVerificationMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         print(f"request.path---->{request.path}")
#             # Extract the HMAC from the request headers
#         referer = request.META.get('HTTP_REFERER', 'Unknown')    
#         print(f"referer------------------>{referer}") 
#         request.shopify_referer = referer   

#         if request.path == '/shopify/install/':
#                 full_url = request.build_absolute_uri()
#                 parsed_url = urlparse(full_url)
#                 query_params = parse_qs(parsed_url.query)
#                 hmac_value = query_params.get('hmac', [None])[0]
#                 hmac_received = request.GET.get('hmac')
#                 request.shopify_hmac = hmac_received if hmac_received else hmac_value
#                 print(f"hmac_received----------->{hmac_received}")  
#                 print(f"hmac_value----------->{hmac_value}")  

#         # If the request is valid, pass it along
#         response = self.get_response(request)
#         return response
