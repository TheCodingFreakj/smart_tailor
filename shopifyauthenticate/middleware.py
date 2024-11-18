from django.shortcuts import redirect
from .models import ShopifyStore

class VerifyAppInstallationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        hmac = request.headers.get('X-Shopify-Hmac-Sha256')
        print(hmac)
        if hmac == None:
             return redirect("https://smart-tailor-frnt.onrender.com/error")
        response = self.get_response(request)
        print(response)
        return response