import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
import requests
from shopifyauthenticate.models import ShopifyStore
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from datetime import datetime, timedelta



@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({'csrfToken': request.COOKIES.get('csrftoken')})


@csrf_exempt
def dashboard(request):
    data = json.loads(request.body)
    shop_id = data.get("shopId")
    shop = ShopifyStore.objects.filter(id=shop_id).first()
    headers = {
        'X-Shopify-Access-Token': shop.access_token
    }

    # Make the request to the Shopify API to get shop details
    response = requests.get(f'https://{shop.shop_name}/admin/api/2024-01/shop.json', headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        shop_details = response.json()
        print("Shop Details:", shop_details)
        return JsonResponse({ "shop_details": shop_details }, status=200)
    else:
        print(f"Failed to fetch shop details. Status code: {response.status_code}")
        return JsonResponse({ "error": "No Shop Details" }, status=403)

