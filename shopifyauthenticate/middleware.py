from django.shortcuts import redirect
from .models import ShopifyStore

class VerifyAppInstallationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        shop_domain = request.GET.get('shop')
        if shop_domain:
            shop = ShopifyStore.objects.filter(shop_domain=shop_domain).first()
            if not shop or not shop.is_installed:
                return redirect("https://smart-tailor-frnt.onrender.com/error")

        response = self.get_response(request)
        return response