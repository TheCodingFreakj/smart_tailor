import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views import View
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.decomposition import TruncatedSVD
import requests
from .models import ProductRelationship, UserActivity
from shopifyauthenticate.models import ShopifyStore
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from datetime import datetime, timedelta
from rest_framework import status
import shopify
from django.utils.decorators import method_decorator
from smarttailor import settings
from sklearn.metrics.pairwise import cosine_similarity
import certifi



@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({'csrfToken': request.COOKIES.get('csrftoken')})


@csrf_exempt
def dashboard(request):
    data = json.loads(request.body)
    shop_id = data.get("shopId")
    shop = ShopifyStore.objects.filter(id=shop_id).first()
    if hasattr(request, 'auth') and request.auth:
        
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
            shop_id_from_shopify = shop_details["shop"]["id"]
            shop.shop_id_from_shopify = shop_id_from_shopify
            shop.save()
            return JsonResponse({ "shop_details": shop_details, "shop":shop_details["shop"]["domain"] }, status=200)
        else:
            print(f"Failed to fetch shop details. Status code: {response.status_code}")
            return JsonResponse({ "error": "No Shop Details","shop":shop_details["shop"]["domain"] }, status=403)
    else:
        if shop:
            shop.urlsPassed = ''
            shop.save()
        return JsonResponse({'error': 'Authentication failed'}, status=403)
    



@method_decorator(csrf_exempt, name='dispatch')
class ProductRecommendationView(View):
    #TRACKING_SCRIPT_URL = "https://c9e3-2409-4062-4d09-af42-306a-f08-54b-74c1.ngrok-free.app/static/recommendations/shopify-tracker.js"
    TRACKING_SCRIPT_URL = f"{settings.SHOPIFY_APP_URL}/static/recommendations/shopify-tracker.js"
    def post(self, request):
        """
        Handle POST requests for multiple actions like script installation, 
        fetching recommendations, or updating preferences.
        """

        data = json.loads(request.body)
        action = data.get("action")
        shop_id = data.get("shopId")
        shop = ShopifyStore.objects.filter(id=shop_id).first()

        if hasattr(request, 'auth') and request.auth:
            if action == "install_script":
                return self.install_tracking_script(request, shop)
            elif action == 'remove_script':
               return self.remove_tracking_script(request, shop)
            else:
                return JsonResponse({"error": "Invalid action specified"}, status=400)
        else:
            if shop:
                shop.urlsPassed = ''
                shop.save()
            return JsonResponse({'error': 'Authentication failed'}, status=403)
        

    def get(self, request):
        """
        Handle GET requests for actions like retrieving metrics or testing endpoints.
        """
        action = request.GET.get("action")

        if action == "get_metrics":
            return self.get_metrics(request)
        elif action == "test_endpoint":
            return JsonResponse({"message": "Test successful"})
        else:
            return JsonResponse({"error": "Invalid action specified"}, status=400)
        
    def remove_tracking_script(self, request, shop):
        """
        Remove the tracking script from the Shopify store.
        """
        data = json.loads(request.body)
        shop_id = data.get("shopId")

        if not shop_id:
            return JsonResponse({"error": "Missing shop URL or access token"}, status=400)

        try:
            # Shopify API session initialization
            api_version = '2024-10'  # Update this to the appropriate API version
            session = shopify.Session(f"https://{shop.shop_name}", api_version, shop.access_token)
            shopify.ShopifyResource.activate_session(session)

            # Fetch all existing scripts
            existing_scripts = shopify.ScriptTag.find()
            script_to_remove = None

            # Find the script we added earlier
            for script in existing_scripts:
                print(script.src)
                if script.src == self.TRACKING_SCRIPT_URL:  # Replace with your script's URL
                    script_to_remove = script
                    break

            # If the script was found, remove it
            if script_to_remove:
                script_to_remove.destroy()
                return JsonResponse({"success": True, "message": "Script removed successfully"})
            else:
                return JsonResponse({"error": "Script not found"}, status=404)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        

    def install_tracking_script(self, request,shop):
        """
        Install the tracking script into the Shopify store.
        """

        data = json.loads(request.body)
        shop_id = data.get("shopId")
        

        if not shop_id:
            return JsonResponse({"error": "Missing shop URL or access token"}, status=400)

        # Shopify API session initialization
        try:


            api_version = '2024-10'
            session = shopify.Session(f"https://{shop.shop_name}", api_version, shop.access_token)
            shopify.ShopifyResource.activate_session(session)

            # Check if script already exists
            existing_scripts = shopify.ScriptTag.find()
            for script in existing_scripts:
                if script.src == self.TRACKING_SCRIPT_URL:
                    return JsonResponse({"success": True, "message": "Script already installed"})

            # Create a new ScriptTag
            script_tag = shopify.ScriptTag.create({
                "event": "onload",  # Load script when the page loads
                "src": self.TRACKING_SCRIPT_URL
            })

            # Handle errors
            if script_tag.errors:
                return JsonResponse({"error": script_tag.errors.full_messages()}, status=400)

            return JsonResponse({"success": True, "message": "Script installed successfully"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


from rest_framework.views import APIView 


# @method_decorator(csrf_exempt, name='dispatch')
# class TrackActivityView(APIView):
#     def post(self, request, *args, **kwargs):
#         print(request.data)

@method_decorator(csrf_exempt, name='dispatch')
class TrackActivityView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract activity data from the request
        activity_data = request.data
        shop = activity_data["shop"]

        
        # self.upload_app_block_to_theme(shop,'2024-10')
        print("Checkin")
        

        
        print("Received activity data:", request.data)

        if activity_data:
            shop_name = activity_data["shop"]
            customerId = activity_data["customerId"] or 1
            shop = ShopifyStore.objects.filter(shop_name=shop_name).first()
            api_version = '2024-10'
            self.install_customer_tracking_script(shop.shop_name, shop.access_token)
            # 2024-10
            
            

            UserActivity.objects.create(
                product_url=activity_data["url"] if "url" in activity_data else 'NA',
                user_id=customerId,
                product_id=activity_data["product_id"] if "product_id" in activity_data else 'NA' ,
                action_type=activity_data["action"],
            )

            if activity_data["action"] == "show_related_viewed_product_based_on_user":
                self.get_related_products_user(activity_data, shop,api_version)
            elif(activity_data["action"] == "show_related_product_based_on_category"):
                self.fetch_shopify_product_category(activity_data["product_id"], shop,api_version)
        return JsonResponse({"message": "Activity tracked successfully"}, status=status.HTTP_200_OK)


#     def fetch_shopify_product_category(self,product_id, shop,api_version):
#         # # GraphQL endpoint URL for Shopify API
#         # url = f"https://{shop.shop_name}/admin/api/{api_version}/graphql.json"

#         # # Headers for the request
#         # headers = {
#         #     "Content-Type": "application/json",
#         #     "X-Shopify-Access-Token": shop.access_token
#         # }

#         #         # GraphQL query
#         # query = """
#         # {
#         # newestProducts: products(first: 5, reverse: true) {
#         #     edges {
#         #     node {
#         #         id
#         #         title
#         #         category{
#         #            name
                
#         #         }
#         #     }
#         #     }
#         # }
#         # oldestProducts: products(first: 5) {
#         #     edges {
#         #     node {
#         #         id
#         #         title
#         #         category{
#         #            name
                
#         #         }
#         #     }
#         #     }
#         # }
#         # }
#         # """

#         # # Data to send in the request
#         # data = {
#         #     "query": query
#         # }


#         data =  {
#   "data": {
#     "newestProducts": {
#       "edges": [
#         {
#           "node": {
#             "id": "gid://shopify/Product/8942110638335",
#             "title": "ew",
#             "category": {
#               "name": "Business & Productivity Software"
#             }
#           }
#         },
#         {
#           "node": {
#             "id": "gid://shopify/Product/8942110376191",
#             "title": "p1",
#             "category": {
#               "name": "Educational Software"
#             }
#           }
#         }
#       ]
#     },
#     "oldestProducts": {
#       "edges": [
#         {
#           "node": {
#             "id": "gid://shopify/Product/8942110376191",
#             "title": "p1",
#             "category": {
#               "name": "Educational Software"
#             }
#           }
#         },
#         {
#           "node": {
#             "id": "gid://shopify/Product/8942110638335",
#             "title": "ew",
#             "category": {
#               "name": "Business & Productivity Software"
#             }
#           }
#         }
#       ]
#     }
#   },
#   "extensions": {
#     "cost": {
#       "requestedQueryCost": 16,
#       "actualQueryCost": 8,
#       "throttleStatus": {
#         "maximumAvailable": 2000.0,
#         "currentlyAvailable": 1992,
#         "restoreRate": 100.0
#       }
#     }
#   }
# }






#         # Extracting product information (id, title, and category) from newestProducts and oldestProducts
#         newest_products = [product['node'] for product in data['data']['newestProducts']['edges']]
#         oldest_products = [product['node'] for product in data['data']['oldestProducts']['edges']]

#         # Combine all products into a single list
#         all_products = newest_products + oldest_products

#         # Transform the data into the desired format
#         formatted_products = [{"id": product["id"].split('/')[-1], "title": product["title"], "category": product["category"]["name"]} for product in all_products]

#         # Display the formatted products
#         print(formatted_products)


#         # Initialize an empty dictionary to store product IDs and related products
#         products_db = {}
#         all_categories = []

#         # Iterate over the products to populate the database with related products
#         for product in formatted_products:
#             product_id = product['id']
#             product_title = product['title']
#             product_category = product['category'].lower().strip()
#             all_categories.append(product_category)
            
#             # Initialize related products list for each product
#             related_products = []
#             # Find related products by matching categories (exact match or contains)
#             for related_product in formatted_products:

#                 related_product_category = related_product['category'].lower().strip()
#                 if product_id != related_product['id']:

#                     if(related_product_category in all_categories ):
#                         if related_product['id'] not in related_products:
#                            related_products.append(related_product['id'])
                    
    

            
#             # Populate the products_db dictionary with product details and its related products
#             products_db[product_id] = related_products
#         print(products_db)

#        # Iterate through the dictionary and store values in the database
#         for product_id, related_product_ids in products_db.items():
#             # Create a ProductRelationship record for each product with its related products
#             ProductRelationship.objects.create(
#                 product_id=product_id,
#                 related_product_ids=related_product_ids
#             )



            

            
        # Send POST request to Shopify API
        # response = requests.post(url, headers=headers, json=data,verify=certifi.where())

        # # Check if the request was successful
        # if response.status_code == 200:
        #     response_data = response.json()
        #     print(json.dumps(response_data, indent=2))  # Pretty print the response
        # else:
        #     print(f"Error: {response.status_code}, {response.text}")
        # Calculate the date for one week ago
        
    def get_related_products_user(self,activity_data,shop,version):
        
    
        # customer_id = activity_data["customerId"]
        # query = f"""
        # {{
        # orders(first: 10, query: "{f'customer_id:{customer_id}'}") {{
        #     edges {{
        #     node {{
        #         id
        #         updatedAt
        #         customer{{
        #         id
        #         }}
        #         customerJourney{{
        #             customerOrderIndex
        #             daysToConversion
        #             firstVisit{{
        #             source
        #             }}
        #             moments{{
        #             occurredAt
        #             }}
        #             lastVisit{{
        #             source
        #             }}
        #         }}
                
        #         lineItems(first:5){{
        #           edges{{
        #           node{{
        #           name
        #           quantity
        #           product{{
        #           category{{
        #           name
        #           }}
        #           title
        #           variants(first: 5){{
        #           nodes{{
        #           displayName
        #           price
                  
        #           }}
        #           }}
        #           }}
        #           }}
        #           }}
        #         }}
        #     }}
        #     }}
        # }}
        # }}
        # """

        # # Prepare the headers
        # headers = {
        #     "Content-Type": "application/json",
        #     "X-Shopify-Access-Token": shop.access_token
        # }

        # # Prepare the payload
        # payload = {
        #     "query": query,
           
        # }

        # # Make the POST request to the Shopify API
        # response = requests.post(f"https://{shop.shop_name}/admin/api/{version}/graphql.json", headers=headers, data=json.dumps(payload),verify=certifi.where())
        # print(response.json())

        # # Check if the request was successful
        # if response.status_code == 200:
        #     data = response.json()  # Parse the response JSON
        #     print(json.dumps(data, indent=2))  # Pretty print the response
        # else:
        #     print(f"Error: {response.status_code}, {response.text}")



        # Define the GraphQL query
        # query = """
        
        # products(first: 10, reverse: true) {
        #     edges {
        #     node {
        #         title
        #     }
        #     }
        # }
        
        # """

        # # Define the headers (if any authorization token is needed, for example)
        # headers = {
        #     'Content-Type': 'application/json',
        #     "X-Shopify-Access-Token": shop.access_token  # Replace with your actual token
        # }

        # # Make the POST request to the GraphQL endpoint
        # response = requests.post(f"https://{shop.shop_name}/admin/api/{version}/graphql.json", json={'query': query}, headers=headers)
        # all_products = None
        # # Check the status code and print the response
        # if response.status_code == 200:
        #     data = response.json()  # Parse the response JSON data
        #     # Pretty print the data (if needed)
        #     import json
        #     print(json.dumps(data, indent=2))  # Print the JSON response in a readable format
        # else:
        #     print(f"Failed to fetch data: {response.status_code}")

        response_data = {
  "data": {
    "products": {
      "edges": [
        {
          "node": {
            "title": "ssss"
          }
        },
        {
          "node": {
            "title": "drgdgdfgrdrf"
          }
        },
        {
          "node": {
            "title": "dvdgvdf"
          }
        },
        {
          "node": {
            "title": "fsfsfcsd"
          }
        },
        {
          "node": {
            "title": "ew"
          }
        },
        {
          "node": {
            "title": "p1"
          }
        }
      ]
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 6,
      "actualQueryCost": 5,
      "throttleStatus": {
        "maximumAvailable": 2000.0,
        "currentlyAvailable": 1995,
        "restoreRate": 100.0
      }
    }
  }
}
        # Extracting product titles
        all_products_in_store = [product['node']['title'] for product in response_data['data']['products']['edges']]

        # Print the result
        print(all_products_in_store)
        data = {'data': {'orders': {'edges': [{'node': {'id': 'gid://shopify/Order/5892709744895', 'updatedAt': '2024-11-29T16:28:59Z', 'customer': {'id': 'gid://shopify/Customer/7664803578111'}, 'customerJourney': {'customerOrderIndex': 0, 'daysToConversion': 1, 'firstVisit': {'source': 'direct'}, 'moments': [{'occurredAt': '2024-11-28T16:51:42Z'}, {'occurredAt': '2024-11-29T16:08:15Z'}, {'occurredAt': '2024-11-29T16:26:02Z'}], 'lastVisit': {'source': 'https://shopify.com/'}}, 'lineItems': {'edges': [{'node': {'name': 'ssss', 'quantity': 1, 'product': {'category': {'name': 'Educational Toys'}, 'title': 'ssss', 'variants': {'nodes': [{'displayName': 'ssss - Default Title', 'price': '222.00'}]}}}}]}}}, {'node': {'id': 'gid://shopify/Order/5892711776511', 'updatedAt': '2024-11-29T16:29:30Z', 'customer': {'id': 'gid://shopify/Customer/7664803578111'}, 'customerJourney': {'customerOrderIndex': 0, 'daysToConversion': 1, 'firstVisit': {'source': 'direct'}, 'moments': [{'occurredAt': '2024-11-29T16:29:03Z'}], 'lastVisit': None}, 'lineItems': {'edges': [{'node': {'name': 'drgdgdfgrdrf', 'quantity': 1, 'product': {'category': {'name': 'Computer Software'}, 'title': 'drgdgdfgrdrf', 'variants': {'nodes': [{'displayName': 'drgdgdfgrdrf - Default Title', 'price': '2.00'}]}}}}]}}}]}}, 'extensions': {'cost': {'requestedQueryCost': 130, 'actualQueryCost': 16, 'throttleStatus': {'maximumAvailable': 2000.0, 'currentlyAvailable': 1984, 'restoreRate': 100.0}}}}
        #data={'data': {'orders': {'edges': [{'node': {'id': 'gid://shopify/Order/5887448056063', 'updatedAt': '2024-11-27T10:06:04Z', 'customer': {'id': 'gid://shopify/Customer/7656824865023'}, 'customerJourney': {'customerOrderIndex': 0, 'daysToConversion': 3, 'firstVisit': {'source': 'direct'}, 'moments': [{'occurredAt': '2024-11-24T19:28:53Z'}, {'occurredAt': '2024-11-26T17:55:17Z'}, {'occurredAt': '2024-11-26T18:43:16Z'}, {'occurredAt': '2024-11-26T22:45:25Z'}, {'occurredAt': '2024-11-27T06:00:21Z'}], 'lastVisit': {'source': 'direct'}}, 'lineItems': {'edges': [{'node': {'name': 'p1', 'quantity': 7, 'product': {'category': {'name': 'Educational Software'}, 'title': 'p1', 'variants': {'nodes': [{'displayName': 'p1 - Default Title', 'price': '11.00'}]}}}}]}}}, {'node': {'id': 'gid://shopify/Order/5887563170047', 'updatedAt': '2024-11-27T11:01:32Z', 'customer': {'id': 'gid://shopify/Customer/7656824865023'}, 'customerJourney': {'customerOrderIndex': 0, 'daysToConversion': 1, 'firstVisit': {'source': 'direct'}, 'moments': [{'occurredAt': '2024-11-27T07:52:10Z'}], 'lastVisit': None}, 'lineItems': {'edges': [{'node': {'name': 'p1', 'quantity': 1, 'product': {'category': {'name': 'Educational Software'}, 'title': 'p1', 'variants': {'nodes': [{'displayName': 'p1 - Default Title', 'price': '11.00'}]}}}}]}}}, {'node': {'id': 'gid://shopify/Order/5890372894975', 'updatedAt': '2024-11-28T15:21:53Z', 'customer': {'id': 'gid://shopify/Customer/7656824865023'}, 'customerJourney': {'customerOrderIndex': 0, 'daysToConversion': 1, 'firstVisit': {'source': 'direct'}, 'moments': [{'occurredAt': '2024-11-27T11:07:35Z'}, {'occurredAt': '2024-11-27T12:47:39Z'}, {'occurredAt': '2024-11-28T15:07:57Z'}], 'lastVisit': {'source': 'direct'}}, 'lineItems': {'edges': [{'node': {'name': 'p1', 'quantity': 1, 'product': {'category': {'name': 'Educational Software'}, 'title': 'p1', 'variants': {'nodes': [{'displayName': 'p1 - Default Title', 'price': '11.00'}]}}}}]}}}, {'node': {'id': 'gid://shopify/Order/5890492793087', 'updatedAt': '2024-11-28T16:51:13Z', 'customer': {'id': 'gid://shopify/Customer/7656824865023'}, 'customerJourney': {'customerOrderIndex': 0, 'daysToConversion': 1, 'firstVisit': {'source': 'direct'}, 'moments': [{'occurredAt': '2024-11-28T15:22:02Z'}, {'occurredAt': '2024-11-28T15:24:57Z'}], 'lastVisit': {'source': 'https://shopify.com/'}}, 'lineItems': {'edges': [{'node': {'name': 'fsfsfcsd', 'quantity': 5, 'product': {'category': {'name': 'Business & Productivity Software'}, 'title': 'fsfsfcsd', 'variants': {'nodes': [{'displayName': 'fsfsfcsd - Default Title', 'price': '1111.00'}]}}}}]}}}, {'node': {'id': 'gid://shopify/Order/5890493579519', 'updatedAt': '2024-11-28T16:51:40Z', 'customer': {'id': 'gid://shopify/Customer/7656824865023'}, 'customerJourney': None, 'lineItems': {'edges': [{'node': {'name': 'ssss', 'quantity': 4, 'product': {'category': {'name': 'Educational Toys'}, 'title': 'ssss', 'variants': {'nodes': [{'displayName': 'ssss - Default Title', 'price': '222.00'}]}}}}]}}}]}}, 'extensions': {'cost': {'requestedQueryCost': 130, 'actualQueryCost': 41, 'throttleStatus': {'maximumAvailable': 2000.0, 'currentlyAvailable': 1959, 'restoreRate': 100.0}}}}
        # Initialize an empty list to store the extracted data
        orders = data.get("data", {}).get("orders", {}).get("edges", [])
        customer_data = []

        for order in orders:
            node = order.get("node", {})
            customer_journey = node.get("customerJourney") if node.get("customerJourney") is not None else {}

            # Safely extract customerJourney fields with additional None checks
            order_index = customer_journey.get("customerOrderIndex") if customer_journey else None
            days_to_conversion = customer_journey.get("daysToConversion") if customer_journey else None
            first_visit_source = (
                customer_journey.get("firstVisit", {}).get("source") if customer_journey and customer_journey.get("firstVisit") else None
            )
            last_visit_source = (
                customer_journey.get("lastVisit", {}).get("source") if customer_journey and customer_journey.get("lastVisit") else None
            )
            moments = (
                [
                    {"occurredAt": moment.get("occurredAt")}
                    for moment in customer_journey.get("moments", [])
                ]
                if customer_journey and customer_journey.get("moments")
                else []
            )

            line_items = node.get("lineItems", {}).get("edges", [])

            for item in line_items:
                product_data = item.get("node", {})
                product = product_data.get("product", {})
                variants = product.get("variants", {}).get("nodes", [])

                customer_data.append({
                    "customer_id": node.get("customer", {}).get("id"),
                    "product_name": product_data.get("name"),
                    "quantity": product_data.get("quantity"),
                    "category": product.get("category", {}).get("name"),
                    "variants": [
                        {"displayName": variant.get("displayName"), "price": variant.get("price")}
                        for variant in variants
                    ],
                    "order_index": order_index,
                    "days_to_conversion": days_to_conversion,
                    "first_visit_source": first_visit_source,
                    "last_visit_source": last_visit_source,
                    "moments": moments,
                    "order_updated_at": node.get("updatedAt"),
                })

        # Return the customer_data or process it as needed
        # Extracting customer data: interactions (product, quantity)
        customer_interactions = {(entry['product_name'], entry['quantity']) for entry in customer_data}
        # List of unique customers and products
        customers = [f'gid://shopify/Customer/{activity_data["customerId"]}']  # Single logged-in customer
        products = all_products_in_store  # All products in the store

        # Initialize the interaction matrix with zeros
        interaction_matrix = np.zeros((len(customers), len(products)))
        print("interaction_matrix", interaction_matrix)

        # Map customer and product names to indices
        customer_to_index = {customer: idx for idx, customer in enumerate(customers)}
        product_to_index = {product: idx for idx, product in enumerate(products)}

        # Fill the interaction matrix with quantities
        for entry in customer_data:
            customer_idx = customer_to_index[entry['customer_id']]
            product_idx = product_to_index[entry['product_name']]
            interaction_matrix[customer_idx, product_idx] += entry['quantity']  # Adding interaction (quantity)

        # Convert interaction matrix to DataFrame for better visualization
        import pandas as pd
        interaction_df = pd.DataFrame(interaction_matrix, index=customers, columns=products)

        print(interaction_df)

        from sklearn.decomposition import TruncatedSVD

        # Apply SVD to the interaction matrix
        svd = TruncatedSVD(n_components=3, random_state=42)
        svd_matrix = svd.fit_transform(interaction_matrix)

        # Reconstruct the matrix
        reconstructed_matrix = svd.inverse_transform(svd_matrix)

        # Example: Recommend products for the first customer (customer 0)
        customer_index = 0
        customer_scores = reconstructed_matrix[customer_index]

        # Get products that the customer hasn't interacted with yet
        predicted_interests = []
        for product_index, score in enumerate(customer_scores):
            if interaction_matrix[customer_index, product_index] == 0:  # Not interacted with
                predicted_interests.append((products[product_index], score))

        # Sort products by predicted score
        predicted_interests.sort(key=lambda x: x[1], reverse=True)

        # Display top 5 recommended products
        top_recommended_products = predicted_interests[:5]
        print(f"Top recommended products for customer {customers[customer_index]}: {top_recommended_products}")
        # # Convert to DataFrame
        # df = pd.DataFrame(customer_data)

        # # Extract price from the 'variants' list
        # # Convert to DataFrame
        # df = pd.DataFrame(customer_data)
        # print(df)

        # # Extract price from the 'variants' column
        # df['price'] = df['variants'].apply(lambda x: float(x[0]['price']) if isinstance(x, list) and x else None)
        # print(df[['customer_id', 'product_name', 'variants', 'price']])
        # # Fill missing values in 'last_visit_source' with 'unknown'
        # df['last_visit_source'].fillna('unknown', inplace=True)

        # # One-Hot Encoding for categorical columns
        # encoder = OneHotEncoder(drop='first', sparse_output=False)
        # encoded_columns = encoder.fit_transform(df[['first_visit_source', 'last_visit_source']])
        # encoded_df = pd.DataFrame(encoded_columns, columns=encoder.get_feature_names_out())

        # # Concatenate with the original DataFrame and drop the original categorical columns
        # df = pd.concat([df, encoded_df], axis=1)
        # df.drop(['first_visit_source', 'last_visit_source'], axis=1, inplace=True)

        # # Display processed DataFrame
        # print(df.head())



        # # Parse timestamps
        # df['order_updated_at'] = pd.to_datetime(df['order_updated_at'])

        # # Calculate recency of the last order (days since last order)
        # df['order_updated_at'] = pd.to_datetime(df['order_updated_at']).dt.tz_convert('UTC')
        # df['days_since_last_purchase'] = (pd.to_datetime('now', utc=True) - df['order_updated_at']).dt.days


        # # Aggregate data by customer
        # customer_summary = df.groupby('customer_id').agg({
        #     'quantity': 'sum',       # Total quantity purchased
        #     'price': 'mean',         # Average price
        #     'days_since_last_purchase': 'mean',  # Mean days since last purchase
        # }).reset_index()

        # # Display aggregated customer data
        # print(customer_summary)


        # # Create customer-product matrix (pivot table)
        # customer_product_matrix = df.pivot_table(index='customer_id', columns='product_name', values='quantity', aggfunc='sum', fill_value=0)
        # from tabulate import tabulate
        # # Display matrix
        # print(tabulate(customer_product_matrix, headers='keys', tablefmt='pretty'))

        # customer_product_matrix = np.nan_to_num(customer_product_matrix, nan=0)

        # print(customer_product_matrix)
        


        # from sklearn.decomposition import TruncatedSVD

        # # Step 1: Apply Singular Value Decomposition (SVD) on the customer’s data
        # svd = TruncatedSVD(n_components=3, random_state=42)
        # svd_matrix = svd.fit_transform(customer_product_matrix)

        # # Step 2: Reconstruct the original matrix (approximately) based on SVD
        # reconstructed_matrix = svd.inverse_transform(svd_matrix)

        # # Step 3: Recommend products for the logged-in customer
        # # Extract scores for the logged-in customer (which is the only row in the matrix)
        # customer_scores = reconstructed_matrix[0]

        # print(f"Customer scores (reconstructed matrix): {customer_scores}")

        # # Step 4: Get products with the highest predicted scores that the customer has not interacted with yet
        # predicted_interests = []
        # for product_index, score in enumerate(customer_scores):
        #     if customer_product_matrix[0, product_index] == 0:  # Product not interacted with
        #         predicted_interests.append((product_index, score))

        # # Sort products by predicted score in descending order (higher scores mean higher likelihood of interest)
        # predicted_interests.sort(key=lambda x: x[1], reverse=True)

        # # Display top 5 recommended products for the logged-in customer
        # top_recommended_products = predicted_interests[:5]

        # # Output recommended products (example: product indices and scores)
        # print(f"Top recommended products for the logged-in customer: {top_recommended_products}")


    def install_customer_tracking_script(self,shop,access_token):
        """
        Install the tracking script into the Shopify store.
        """
        api_version = '2024-10'
        # The URL to compare against
        target_url = f"{settings.SHOPIFY_APP_URL}/static/recommendations/shopify-tracker.js"
        endpoint = f"https://{shop}/admin/api/2024-10/script_tags.json"

        payload = {
        "script_tag": {
            "event": "onload",
            "src": f"{settings.SHOPIFY_APP_URL}/static/recommendations/customer-tracking.js"
        }
        }

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token
        }


        response = requests.get(endpoint, headers=headers)
        script_tags = response.json().get('script_tags', [])

        print(script_tags)


        for script_tag in script_tags:
            script_url = script_tag.get('src')
            
            # Check if the URL is not equal to the target URL
            if script_url != target_url:
                script_id = script_tag['id']
                delete_endpoint = f"https://{shop}/admin/api/2024-10/script_tags/{script_id}.json"
                
                delete_response = requests.delete(delete_endpoint, headers=headers)
                if delete_response.status_code == 200:
                    print(f"Deleted script tag with ID: {script_id}")
                else:
                    print(f"Failed to delete script tag with ID: {script_id}, Response: {delete_response.json()}")
            else:
                print(f"Skipping deletion of script tag with ID: {script_tag['id']} (URL matches the target URL)")

        # response = requests.post(endpoint, json=payload, headers=headers)
        # print(response.json())





@method_decorator(csrf_exempt, name='dispatch')
class ShopifyThemeUpdater(View):

    def post(self, request):

        data = json.loads(request.body)
        version = '2024-10'
        shop_id = data.get("shopId")
        shop = ShopifyStore.objects.filter(id=shop_id).first()
        # Initialize the Shopify session (use correct API version and access token)
        session = shopify.Session(shop.shop_name, version, shop.access_token)
        shopify.ShopifyResource.activate_session(session)

        # Fetch themes
        url = f'https://{shop.shop_name}/admin/api/{version}/themes.json'
        headers = {
            'X-Shopify-Access-Token': shop.access_token  # Include the access token in the header
        }

        response = requests.get(url, headers=headers)
        print(response.status_code)

        main_theme = None
        if response.status_code == 200:
            themes = response.json().get('themes', [])
            main_theme = [theme for theme in themes if theme.get('role') == 'main']
            if main_theme:
                print(f"Main theme found: {main_theme[0]['name']}")
            else:
                print("No main theme found")
        else:
            raise Exception(f"Error fetching themes: {response.status_code}, {response.text}")

        if not main_theme:
            raise Exception("No main theme found")
        
        theme_id = main_theme[0]["id"]
        print(f"Main theme ID: {theme_id}")

        # Fetch the 'theme.liquid' content
        url = f"https://{shop.shop_name}/admin/api/{version}/themes/{theme_id}/assets.json"
        params = {"asset[key]": "layout/theme.liquid"}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            theme_content = response.json().get("asset", {}).get("value")
            if theme_content:
                print("Fetched theme.liquid content successfully.")
                script_to_add = """
                <script>
  {% if customer %}
    window.loggedInCustomer = {
      id: "{{ customer.id }}",
      email: "{{ customer.email }}",
      first_name: "{{ customer.first_name }}",
      last_name: "{{ customer.last_name }}"
    };
    console.log("Logged in customer:", window.loggedInCustomer);
  {% else %}
    console.log("No customer is logged in.");
    window.loggedInCustomer = null;
  {% endif %}
</script>
                """
                updated_liquid = theme_content.replace("</body>", script_to_add + "\n</body>")
                self.update_theme_liquid(theme_id, updated_liquid, shop,version)
                return JsonResponse({"message": "Code Installed successfuly"}, status=status.HTTP_200_OK)
            else:
                print("Error: theme.liquid content is empty.")
        else:
            print(f"Error fetching theme.liquid: {response.status_code}, {response.text}")

    # Step 2: Update the `theme.liquid` File
    def update_theme_liquid(self,theme_id, updated_content, shop, version):
        url = f"https://{settings.SHOPIFY_API_KEY}:{settings.SHOPIFY_API_SECRET}@{shop.shop_name}/admin/api/{version}/themes/{theme_id}/assets.json"
        payload = {
            "asset": {
                "key": "layout/theme.liquid",
                "value": updated_content
            }
        }

        headers = {
    "X-Shopify-Access-Token": shop.access_token
}
        response = requests.put(url, json=payload,headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return JsonResponse({"message": "Code Installed successfuly"}, status=status.HTTP_200_OK)