from django.http import HttpResponse
import requests
from ..shopifyauthenticate.models import ShopifyStore
def home(request):
    shop = ShopifyStore.objects.filter(id=request.body.shopId).first()
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
    else:
        print(f"Failed to fetch shop details. Status code: {response.status_code}")
