import base64
from datetime import datetime, timedelta
import json
import uuid
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
        defaults={'access_token': access_token,'is_installed':"installed"}  # Update the access token
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

        ShopifyStore.objects.update_or_create(
                    shop_name=request.GET.get('shop'),  # Use the shop name as the unique identifier
                    defaults={'calculated_hmac': calculated_hmac}  # Update the access token
        )


        # Verify HMAC
        if hmac_value != calculated_hmac:
            print("HMAC validation failed.")
            print(f"Provided HMAC: {hmac_value}")
            print(f"Calculated HMAC: {calculated_hmac}")
            return HttpResponseBadRequest("HMAC validation failed.")
        # Proceed with redirection
        api_key = settings.SHOPIFY_API_KEY
        redirect_uri = f"{settings.SHOPIFY_APP_URL}/shopify/callback/"
        # write_themes_assets
        scopes = "read_products,write_products,read_orders,write_orders,read_publications,read_draft_orders,read_script_tags,write_script_tags,read_customers,write_customers,read_themes,write_themes,read_customers,write_customers"
        # Create a session token (it could be a random UUID or something more specific)
        session_token = str(uuid.uuid4())
        request.session['shopify_oauth_session_token'] = session_token

        oauth_url = f"https://{shop}/admin/oauth/authorize?client_id={api_key}&scope={scopes}&redirect_uri={redirect_uri}&state=nonce"
        print(f"Redirecting to OAuth URL: {oauth_url}")

        return redirect(oauth_url)


    

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import hashlib
import hmac
from django.utils.timezone import make_aware


@csrf_exempt
def check_installation_status(request):
    print(request.GET)
    data = json.loads(request.body)
    shop_id = data.get("shop")





 
        


import requests
from django.conf import settings
from django.http import JsonResponse


from django.http import HttpResponse
@csrf_exempt
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
            shop.delete()
            print(f"Shop {shop_domain} has been deleted.")

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
        shopify_hmac = ShopifyStore.objects.filter(shop_name=shop).first()
        

        # Exchange the code for an access token
        token_url = f"https://{shop}/admin/oauth/access_token"
        payload = {
            "client_id": settings.SHOPIFY_API_KEY,
            "client_secret": settings.SHOPIFY_API_SECRET,
            "code": code,
        }
        response = requests.post(token_url, data=payload)



        print(response.json())

        if response.status_code == 200:
            access_token = response.json().get("access_token")

            # Save shop details
            save_access_token(shop, access_token)

            # Register the app/uninstalled webhook
            webhook_url = f"{settings.SHOPIFY_APP_URL}/webhooks/app_uninstalled/"
            success, message = register_uninstall_webhook(shop, access_token, webhook_url)
            if not success:
                print(f"Failed to register uninstall webhook: {message}")
            print(f"Hitting here--->{code}")
            shopRecord = ShopifyStore.objects.filter(shop_name=shop).first()  
            shopRecord.is_installed == "installed"  

            # Redirect to React app
            react_home_url = f"{settings.SHOPIFY_APP_URL_FRNT}/dashboard/{shop}/{shopRecord.id}"


            # Validate session token (ensures this was a valid redirect flow)
            if not code:
                print("Hitting here")
                return redirect(f"{settings.SHOPIFY_APP_URL_FRNT}/error")
            else:
                print(f"Hitting here---{react_home_url}")
                return redirect(react_home_url)


        # Redirect to an error page if token exchange fails
        return redirect(f"{settings.SHOPIFY_APP_URL_FRNT}/error")


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
