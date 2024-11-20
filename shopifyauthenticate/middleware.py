from urllib.parse import urlparse, parse_qs
from django.utils.deprecation import MiddlewareMixin

class ShopifyAuthMiddleware(MiddlewareMixin):
    def __init__(self):
        self.url_paths = []  
    
    def process_request(self, request):
        print("Executing before the view.")

        self.url_paths.append(request.path)
        
        request.referer = request.META.get('HTTP_REFERER', 'Unknown')  
        request.path_params = self.url_paths
        return None  # Continue processing the request

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
