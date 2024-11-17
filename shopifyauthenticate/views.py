import requests
from django.shortcuts import redirect
from django.conf import settings
from django.http import JsonResponse
from urllib.parse import urlencode
import hashlib
import hmac
from .models import ShopifyStore

# Shopify OAuth Callback URL
def shopify_callback(request):
    # Step 1: Extract the necessary parameters from Shopify's callback request
    shop = request.GET.get('shop')
    code = request.GET.get('code')
    hmac_signature = request.GET.get('hmac_sha256')
    
    # Step 2: Verify the request is coming from Shopify using the HMAC signature
    if not verify_shopify_signature(request.GET, hmac_signature):
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Step 3: Exchange the authorization code for an access token
    access_token = exchange_code_for_token(shop, code)

    if access_token:
        # Save the access token securely (e.g., in your database)
        # You might want to associate the access token with the shop's details.
        save_access_token(shop, access_token)
        
        # Redirect the merchant to a success page or your app's dashboard
        return redirect('success_page')  # Update with your actual page
    
    return JsonResponse({'error': 'Failed to exchange code for access token'}, status=400)

def verify_shopify_signature(params, hmac_signature):
    """
    Verifies the authenticity of the request using the Shopify HMAC-SHA256 signature.
    """
    # Prepare the data to be used for signature generation (shopify does this)
    sorted_params = sorted(params.items())
    query_string = urlencode(sorted_params).encode('utf-8')

    # Verify the HMAC using the shared secret
    secret = settings.SHOPIFY_API_SECRET.encode('utf-8')
    computed_signature = hmac.new(secret, query_string, hashlib.sha256).hexdigest()

    return hmac_signature == computed_signature

def exchange_code_for_token(shop, code):
    """
    Exchanges the authorization code for an access token from Shopify.
    """
    # Prepare the API request to Shopify's access token endpoint
    url = f'https://{shop}/admin/oauth/access_token'
    data = {
        'client_id': settings.SHOPIFY_API_KEY,
        'client_secret': settings.SHOPIFY_API_SECRET,
        'code': code
    }

    # Make the POST request to exchange the code for a token
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        # Return the access token (parse the JSON response)
        return response.json().get('access_token')
    else:
        return None

def save_access_token(shop, access_token):
    """
    Save the access token securely in PostgreSQL database.
    """
    # Store the access token in the database or update it if the shop already exists
    shop_record, created = ShopifyStore.objects.update_or_create(
        shop_name=shop,  # Use the shop name as the unique identifier
        defaults={'access_token': access_token}  # Update the access token
    )
    
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

class ShopifyInstallView(View):
    def get(self, request, *args, **kwargs):
        shop = request.GET.get('shop')
        api_key = settings.SHOPIFY_API_KEY
        redirect_uri = f"{settings.SHOPIFY_APP_URL}/shopify/callback/"
        
        # Define the scopes you need for your app
        scopes = "read_products,write_products,read_orders,write_orders"
        
        oauth_url = f"https://{shop}/admin/oauth/authorize?client_id={api_key}&scope={scopes}&redirect_uri={redirect_uri}&state=nonce"
        
        return redirect(oauth_url)
    

import requests

def get_webhooks(shop_url, access_token):
    url = f"https://{shop_url}/admin/api/2023-01/webhooks.json"
    headers = {
        "X-Shopify-Access-Token": access_token
    }
    response = requests.get(url, headers=headers)
    return response.json()



def delete_webhook(shop_url, access_token, webhook_id):
    url = f"https://{shop_url}/admin/api/2023-01/webhooks/{webhook_id}.json"
    headers = {
        "X-Shopify-Access-Token": access_token
    }
    response = requests.delete(url, headers=headers)
    return response.status_code


import requests
from django.conf import settings
from django.http import JsonResponse




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
