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
from django.conf import settings
from django.http import JsonResponse


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
            return JsonResponse({"message": "App installed successfully"})
        return JsonResponse({"error": "Token exchange failed"}, status=400)    