import base64
import json
import requests
from django.shortcuts import redirect
from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse
from urllib.parse import urlencode
import hashlib
import hmac
from .models import ShopifyStore


def save_access_token(shop, access_token):
    """
    Save the access token securely in PostgreSQL database.
    """
    
    # Store the access token in the database or update it if the shop already exists
    shop_record, created = ShopifyStore.objects.update_or_create(
        shop_name=shop,  # Use the shop name as the unique identifier
        defaults={'access_token': access_token,'is_installed':True}  # Update the access token
    )

    shop_record_retrieved = ShopifyStore.objects.filter(shop_name=shop).first()

    if(shop_record_retrieved):
        shop_record_retrieved.first_time = created
    
    if created:
        print(f"Created new store record for {shop}")
    else:
        print(f"Updated access token for {shop}")
    
    # Optionally, you can return the created or updated shop record
    return shop_record

import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View

import hashlib
import hmac

class ShopifyInstallView(View):
    def get(self, request, *args, **kwargs):
        shop = request.GET.get('shop')
        hmac_value = request.GET.get('hmac')
        query_params = request.GET.dict()

        # Ensure 'shop' is valid
        if not shop:
            return HttpResponseBadRequest("Invalid 'shop' parameter.")

        # Remove 'hmac' from query params before validation
        query_params.pop('hmac', None)

        # Create the message and calculate HMAC
        message = "&".join(f"{key}={value}" for key, value in sorted(query_params.items()))
        calculated_hmac = hmac.new(
            settings.SHOPIFY_API_SECRET.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Verify HMAC
        if hmac_value != calculated_hmac:
            print("HMAC validation failed.")
            print(f"Provided HMAC: {hmac_value}")
            print(f"Calculated HMAC: {calculated_hmac}")
            return HttpResponseBadRequest("HMAC validation failed.")

        # Proceed with redirection
        api_key = settings.SHOPIFY_API_KEY
        redirect_uri = f"{settings.SHOPIFY_APP_URL}/shopify/callback/"
        scopes = "read_products,write_products,read_orders,write_orders"

        oauth_url = f"https://{shop}/admin/oauth/authorize?client_id={api_key}&scope={scopes}&redirect_uri={redirect_uri}&state=nonce"
        print(f"Redirecting to OAuth URL: {oauth_url}")

        return redirect(oauth_url)


    

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def check_installation_status(request):
    if request.method != "POST":
        return JsonResponse(
            {"installed": False, "error": "Invalid request method"}, 
            status=405
        )

    try:
        # Parse JSON body
        data = json.loads(request.body)
        shop_domain = data.get("shop")
        
        if not shop_domain:
            return JsonResponse(
                {"installed": False, "error": "Shop parameter is missing or invalid"}, 
                status=400
            )

        # Check if the shop exists in the database
        shop = ShopifyStore.objects.filter(shop_name=shop_domain).first()

        if shop:
            # Check if the app is installed and if it's the first installation
            if shop.is_installed:
                return JsonResponse({
                    "installed": shop.is_installed, 
                    "first_time": shop.first_time
                })
            else:
                return JsonResponse({
                    "installed": False, 
                    "error": "App is not fully installed"
                }, status=403)
        else:
            # Handle first-time installation case
            return JsonResponse({
                "installed": False, 
                "first_time": True,
                "message": "This is the first installation. Proceed with setup."
            })


    except json.JSONDecodeError:
        return JsonResponse(
            {"installed": False, "error": "Invalid JSON body"}, 
            status=400
        )
import requests
from django.conf import settings
from django.http import JsonResponse


from django.http import HttpResponse

def uninstall_webhook(request):
    shopify_hmac = request.headers.get('X-Shopify-Hmac-Sha256')
    data = request.body
    secret = settings.SHOPIFY_API_SECRET.encode('utf-8')
    hash_calculated = base64.b64encode(
        hmac.new(secret, data, hashlib.sha256).digest()
    ).decode()

    if shopify_hmac != hash_calculated:
        return HttpResponse("Unauthorized", status=401)

    payload = json.loads(data)
    shop_domain = payload.get("domain")
    if shop_domain:
        # Mark the shop as uninstalled
        shop = ShopifyStore.objects.filter(shop_name=shop_domain).first()
        if shop:
            shop.is_installed = False
            shop.save()
            print(f"Shop {shop_domain} marked as uninstalled.")

    return HttpResponse("Webhook processed", status=200)
import requests
from django.conf import settings
from django.shortcuts import redirect
def register_uninstall_webhook(shop, access_token, webhook_url):
    """
    Registers the app/uninstalled webhook for a given shop.
    """
    webhook_payload = {
        "webhook": {
            "topic": "app/uninstalled",
            "address": webhook_url,
            "format": "json"
        }
    }
    headers = {"X-Shopify-Access-Token": access_token}
    response = requests.post(
        f"https://{shop}/admin/api/2023-10/webhooks.json",
        json=webhook_payload,
        headers=headers,
    )
    if response.status_code == 201:
        return True, "Webhook registered successfully"
    elif response.status_code == 422:
        # Check if the webhook already exists
        return False, "Webhook for this topic already exists"
    else:
        return False, response.json()
    

class ShopifyCallbackView(View):
    def get(self, request):
        shop = request.GET.get('shop')
        code = request.GET.get('code')

        # Exchange the code for an access token
        token_url = f"https://{shop}/admin/oauth/access_token"
        payload = {
            "client_id": settings.SHOPIFY_API_KEY,
            "client_secret": settings.SHOPIFY_API_SECRET,
            "code": code,
        }
        response = requests.post(token_url, data=payload)

        print(response)

        if response.status_code == 200:
            access_token = response.json().get("access_token")

            # Save shop details
            save_access_token(shop, access_token)

            # Register the app/uninstalled webhook
            webhook_url = f"{settings.SHOPIFY_APP_URL}/shopify/uninstall-webhook/"
            success, message = register_uninstall_webhook(shop, access_token, webhook_url)
            if not success:
                print(f"Failed to register uninstall webhook: {message}")

            # Redirect to React app
            react_home_url = "https://smart-tailor-frnt.onrender.com/dashboard"
            return redirect(react_home_url)

        # Redirect to an error page if token exchange fails
        return redirect("https://smart-tailor-frnt.onrender.com/error")


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import hmac
import hashlib

class ShopifyUninstallWebhookView(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        shop = request.headers.get("X-Shopify-Shop-Domain")
        hmac_header = request.headers.get("X-Shopify-Hmac-SHA256")
        data = request.body

        # Verify webhook authenticity
        secret = settings.SHOPIFY_API_SECRET
        computed_hmac = hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(computed_hmac, hmac_header):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        # Clean up database
        ShopifyStore.objects.filter(shop_url=shop).delete()

        return JsonResponse({"success": "Webhook received"})
from .models import ShopifyStore

def get_shop_access_token(shop_name):
    try:
        shop = ShopifyStore.objects.get(shop_name=shop_name)
        return shop.access_token
    except ShopifyStore.DoesNotExist:
        raise ValueError(f"No access token found for shop: {shop_name}")
