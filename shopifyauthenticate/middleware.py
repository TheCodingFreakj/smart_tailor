import hashlib
import hmac
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import redirect

class ShopifyHMACVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only validate HMAC for specific endpoints (e.g., those related to Shopify)
        if request.path.startswith('/dashboard/'):
            # Extract the HMAC from the request headers
            hmac_received = request.META.get('HTTP_X_SHOPIFY_HMAC_SHA256')
            print(f"hmac_received----------->{hmac_received}")
            if not hmac_received:
                return JsonResponse({'error': 'Missing HMAC'}, status=400)

            # Extract the query string from the URL
            query_string = request.GET.urlencode()

            # Use your app's shared secret key from Shopify's settings
            secret = settings.SHOPIFY_API_SECRET

            # Calculate the HMAC with the shared secret key and compare it
            calculated_hmac = hmac.new(
                secret.encode('utf-8'), 
                query_string.encode('utf-8'), 
                hashlib.sha256
            ).hexdigest()

            if hmac_received != calculated_hmac:
                return JsonResponse({'error': 'HMAC verification failed'}, status=400)

        # If the request is valid, pass it along
        response = self.get_response(request)
        return response
