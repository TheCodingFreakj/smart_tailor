import hashlib
import hmac
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import redirect

class ShopifyHMACVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"request.path---->{request.path}")
            # Extract the HMAC from the request headers

        if request.path == '/shopify/callback/':
                hmac_received = request.META.get('HTTP_X_SHOPIFY_HMAC_SHA256')
                request.shopify_hmac = hmac_received
                print(f"hmac_received----------->{hmac_received}")    

        # If the request is valid, pass it along
        response = self.get_response(request)
        return response
