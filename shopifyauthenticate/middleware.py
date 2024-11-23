from urllib.parse import urlparse, parse_qs
from django.utils.deprecation import MiddlewareMixin

from .models import ShopifyStore

class ShopifyAuthMiddleware(MiddlewareMixin):

    
    def process_request(self, request):
        print("Executing before the view.")
        
    
        if request.path == '/shopify/callback/':
            code = request.GET.get('code')
            request.code = code
            shop = ShopifyStore.objects.filter(shop_name=request.GET.get('shop')).first()

            if '/shopify/callback/' in shop.urlsPassed.split(","):
                    updated_urls = ','.join(url.strip() for url in shop.urlsPassed.split(',') if url.strip() != '/shopify/callback/') + ', /shopify/callback/'
            else:
                # Add the new path if '/shopify/callback' is not found
                updated_urls = shop.urlsPassed + "," + request.path
            ShopifyStore.objects.filter(shop_name=request.GET.get('shop')).update(
                urlsPassed=updated_urls,
            )    
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

                shop = ShopifyStore.objects.filter(shop_name=request.GET.get('shop')).first()

                if '/shopify/install/' in shop.urlsPassed.split(","):
                     updated_urls = ','.join(url.strip() for url in shop.urlsPassed.split(',') if url.strip() != '/shopify/install/') + ', /shopify/install/'
                else:
                    # Add the new path if '/shopify/install' is not found
                    updated_urls = shop.urlsPassed + "," + request.path
                ShopifyStore.objects.filter(shop_name=request.GET.get('shop')).update(
                    urlsPassed=updated_urls,
                )    
                print(f"hmac_received----------->{hmac_received}")  
                print(f"hmac_value----------->{hmac_value}") 

    def process_response(self, request, response):
        print("Executing after the view.")
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
