import json
from urllib.parse import urlparse, parse_qs
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from datetime import datetime, timedelta
from .models import ShopifyStore
from django.utils.timezone import make_aware


from django.urls import get_resolver
from django.http import JsonResponse

def list_all_urls():
    resolver = get_resolver()

    def extract_patterns(patterns, prefix=""):
        urls = []
        for pattern in patterns:
            if hasattr(pattern, 'url_patterns'):  # If it's an included urlpatterns
                urls.append(f"{prefix}{pattern.pattern}")
                urls.extend(extract_patterns(pattern.url_patterns, prefix + "    "))
            else:
                urls.append(f"{prefix}{pattern.pattern} -> {pattern.callback}")
        return urls

    # Get all URLs
    urls = extract_patterns(resolver.url_patterns)

    return urls

def requestUrls():
    urls = ["/shopify/product-recommendations/"]
    return urls


class ShopifyAuthMiddleware(MiddlewareMixin):
    
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        print("Executing before the view.")
        # Access the view function and its arguments
        print(f"View Function: {view_func.__name__}")
        print(f"View Args: {view_args}")
        print(f"View KWArgs: {view_kwargs}")
        # request.auth = True
        
        print(list_all_urls(), request.path)
        print("refreer------------------------------------------------>", request.META.get('HTTP_REFERER', ''))

        if request.path == '/shopify/install/':
            ShopifyStore.objects.filter(shop_name=request.GET.get('shop', None)).update(
                    urlsPassed=request.META.get('HTTP_REFERER', ''),
                    is_installed="installed"
            )
                 
        if request.path == '/shopify/callback/':
            shop = ShopifyStore.objects.filter(shop_name=request.GET.get('shop', None)).first()


            ShopifyStore.objects.filter(shop_name=request.GET.get('shop', None)).update(
                    urlsPassed=shop.urlsPassed + "," + request.META.get('HTTP_REFERER', ''),
                    is_installed="installed"
            )   
         
   
                # Capture and parse the body if it exists
        if request.method in [ 'POST', 'PUT', 'PATCH']:
            try:
                # Decode and parse the request body as JSON
                body_data = json.loads(request.body.decode('utf-8'))
                print(f"Request Body: {body_data}")
                shop_id = body_data.get("shopId")
                shop = ShopifyStore.objects.filter(id=shop_id).first()

                if shop.urlsPassed == '':
                    request.auth = False
                else:
                    if 'https://admin.shopify.com/' not in shop.urlsPassed.split(","): 
                        if request.path in requestUrls():
                            request.auth = True
                        else:    
                            request.auth = False
                    else:
                        request.auth = True    

      
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error decoding request body: {e}")
 

    def process_response(self, request, response):
        print("Executing after the view.")

 
        if request.path != '/shopify/install/'  or request.path != '/shopify/callback/':

                # Check if the response is a JsonResponse
            if isinstance(response, JsonResponse):
                # Extract the JSON data from the response
                response_data = json.loads(response.content)  # This will give you the dictionary

                if 'shop' in response_data:
                    
                    # Check if 'shop' attribute exists in the response
                    shop = response_data.get('shop')
                    if shop:
                        # You can now use the 'shop' data to update the database or perform other actions
                        print(f"Shop data from response: {shop}")
                        
                        # Example: You can update the database here if needed
                        shop_instance = ShopifyStore.objects.filter(shop_name=shop).first()
                        if shop_instance:
                            shop_instance.urlsPassed = ''
                            shop_instance.save()



        # Optionally, modify the response if needed before returning
        return response
