import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views import View
import pandas as pd
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

                
            
            

            # Respond with a success message
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
        


    def preprocess_data(self,data):
        from sklearn.preprocessing import LabelEncoder
        # Convert 'timestamp' to datetime
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        
        # Extract time-based features
        data['hour_of_day'] = data['timestamp'].dt.hour
        data['day_of_week'] = data['timestamp'].dt.dayofweek

        # Encode 'user_id' and 'action_type' as categorical features
        user_encoder = LabelEncoder()
        data['user_id_encoded'] = user_encoder.fit_transform(data['user_id'])
        
        action_encoder = LabelEncoder()
        data['action_type_encoded'] = action_encoder.fit_transform(data['action_type'])

        # Create features like count of actions by user and product
        user_product_activity = data.groupby(['user_id', 'product_id']).agg({
            'action_type_encoded': ['sum', 'count'],
            'hour_of_day': 'mean',
            'day_of_week': 'mean'
        }).reset_index()

        # Flatten MultiIndex columns
        user_product_activity.columns = ['user_id', 'product_id','product_url', 'action_sum', 'action_count', 'avg_hour_of_day', 'avg_day_of_week']
        
        return user_product_activity

   
    # Step 6: Use the Trained Model for Prediction
    def predict_new_data(self,model, new_data):
        # Preprocess new data
        new_data_processed = self.preprocess_data(new_data)

        # Make predictions on the new data
        X_new = new_data_processed[['action_sum', 'action_count', 'avg_hour_of_day', 'avg_day_of_week']]
        predictions = model.predict(X_new)
        
        return predictions
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

        response_data={'data': {'orders': {'edges': [{'node': {'id': 'gid://shopify/Order/5887448056063', 'updatedAt': '2024-11-27T10:06:04Z', 'customer': {'id': 'gid://shopify/Customer/7656824865023'}, 'customerJourney': {'customerOrderIndex': 0, 'daysToConversion': 3, 'firstVisit': {'source': 'direct'}, 'moments': [{'occurredAt': '2024-11-24T19:28:53Z'}, {'occurredAt': '2024-11-26T17:55:17Z'}, {'occurredAt': '2024-11-26T18:43:16Z'}, {'occurredAt': '2024-11-26T22:45:25Z'}, {'occurredAt': '2024-11-27T06:00:21Z'}], 'lastVisit': {'source': 'direct'}}, 'lineItems': {'edges': [{'node': {'name': 'p1', 'quantity': 7, 'product': {'category': {'name': 'Educational Software'}, 'title': 'p1', 'variants': {'nodes': [{'displayName': 'p1 - Default Title', 'price': '11.00'}]}}}}]}}}, {'node': {'id': 'gid://shopify/Order/5887563170047', 'updatedAt': '2024-11-27T11:01:32Z', 'customer': {'id': 'gid://shopify/Customer/7656824865023'}, 'customerJourney': {'customerOrderIndex': 0, 'daysToConversion': 1, 'firstVisit': {'source': 'direct'}, 'moments': [{'occurredAt': '2024-11-27T07:52:10Z'}], 'lastVisit': None}, 'lineItems': {'edges': [{'node': {'name': 'p1', 'quantity': 1, 'product': {'category': {'name': 'Educational Software'}, 'title': 'p1', 'variants': {'nodes': [{'displayName': 'p1 - Default Title', 'price': '11.00'}]}}}}]}}}, {'node': {'id': 'gid://shopify/Order/5890372894975', 'updatedAt': '2024-11-28T15:21:53Z', 'customer': {'id': 'gid://shopify/Customer/7656824865023'}, 'customerJourney': {'customerOrderIndex': 0, 'daysToConversion': 1, 'firstVisit': {'source': 'direct'}, 'moments': [{'occurredAt': '2024-11-27T11:07:35Z'}, {'occurredAt': '2024-11-27T12:47:39Z'}, {'occurredAt': '2024-11-28T15:07:57Z'}], 'lastVisit': {'source': 'direct'}}, 'lineItems': {'edges': [{'node': {'name': 'p1', 'quantity': 1, 'product': {'category': {'name': 'Educational Software'}, 'title': 'p1', 'variants': {'nodes': [{'displayName': 'p1 - Default Title', 'price': '11.00'}]}}}}]}}}, {'node': {'id': 'gid://shopify/Order/5890492793087', 'updatedAt': '2024-11-28T16:51:13Z', 'customer': {'id': 'gid://shopify/Customer/7656824865023'}, 'customerJourney': {'customerOrderIndex': 0, 'daysToConversion': 1, 'firstVisit': {'source': 'direct'}, 'moments': [{'occurredAt': '2024-11-28T15:22:02Z'}, {'occurredAt': '2024-11-28T15:24:57Z'}], 'lastVisit': {'source': 'https://shopify.com/'}}, 'lineItems': {'edges': [{'node': {'name': 'fsfsfcsd', 'quantity': 5, 'product': {'category': {'name': 'Business & Productivity Software'}, 'title': 'fsfsfcsd', 'variants': {'nodes': [{'displayName': 'fsfsfcsd - Default Title', 'price': '1111.00'}]}}}}]}}}, {'node': {'id': 'gid://shopify/Order/5890493579519', 'updatedAt': '2024-11-28T16:51:40Z', 'customer': {'id': 'gid://shopify/Customer/7656824865023'}, 'customerJourney': None, 'lineItems': {'edges': [{'node': {'name': 'ssss', 'quantity': 4, 'product': {'category': {'name': 'Educational Toys'}, 'title': 'ssss', 'variants': {'nodes': [{'displayName': 'ssss - Default Title', 'price': '222.00'}]}}}}]}}}]}}, 'extensions': {'cost': {'requestedQueryCost': 130, 'actualQueryCost': 41, 'throttleStatus': {'maximumAvailable': 2000.0, 'currentlyAvailable': 1959, 'restoreRate': 100.0}}}}
        # Initialize an empty list to store the extracted data
        extracted_data = []

        # Extract customer, product name, and quantity
        for order in response_data['data']['orders']['edges']:
            customer_id = order['node']['customer']['id'].split('/')[-1]
            for item in order['node']['lineItems']['edges']:
                product_name = item['node']['name']
                quantity = item['node']['quantity']
                extracted_data.append({
                    'customer_id': customer_id,
                    'product_name': product_name,
                    'quantity': quantity
                })

        # Display the extracted data
        print(extracted_data)


        # Convert to DataFrame
        df = pd.DataFrame(extracted_data)

        # Create user-item interaction matrix
        user_item_matrix = df.pivot_table(index='customer_id', columns='product_name', values='quantity', aggfunc='sum', fill_value=0)

        print(user_item_matrix)


        # Perform Singular Value Decomposition (SVD)
        svd = TruncatedSVD(n_components=2)  # We can adjust the number of components
        matrix_svd = svd.fit_transform(user_item_matrix)

        # Reconstruct the matrix
        reconstructed_matrix = svd.inverse_transform(matrix_svd)

        # Get the predicted ratings (approximation)
        predicted_ratings = pd.DataFrame(reconstructed_matrix, columns=user_item_matrix.columns)

        print(predicted_ratings)


                # Compute similarity between products
        product_similarity = cosine_similarity(predicted_ratings.T)

        # Create a DataFrame for easy viewing
        product_similarity_df = pd.DataFrame(product_similarity, index=user_item_matrix.columns, columns=user_item_matrix.columns)

        # Get similar products for a given product, e.g., 'p1'
        similar_products = product_similarity_df['p1'].sort_values(ascending=False)

        # Show top 3 most similar products
        print(similar_products.head(3))


    def upsert_theme_files(self,shop_domain, admin_access_token, theme_id, files):
        """
        Upserts theme files using Shopify GraphQL API.

        Args:
            shop_domain (str): The domain of the Shopify store (e.g., 'your-shop.myshopify.com').
            admin_access_token (str): The admin API access token.
            theme_id (str): The ID of the theme (e.g., 'gid://shopify/OnlineStoreTheme/529529152').
            files (list): A list of file objects to upsert with 'filename' and 'body' content.
        """
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": admin_access_token,
        }

        # GraphQL mutation query and variables
        query = """
        mutation themeFilesUpsert($files: [OnlineStoreThemeFilesUpsertFileInput!]!, $themeId: ID!) {
  themeFilesUpsert(files: $files, themeId: $themeId) {
    upsertedThemeFiles {
      filename
    }
    userErrors {
      field
      message
    }
  }
}
        """

        variables = {
            "themeId": theme_id,
            "files": files
        }

        payload = {
            "query": query,
            "variables": variables
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if "errors" in result:
                    print("Errors returned by Shopify API:")
                    print(json.dumps(result["errors"], indent=4))
                else:
                    print("Theme files upserted successfully:")
                    print(json.dumps(result, indent=4))
            else:
                print(f"Failed to upsert theme files. Status Code: {response.status_code}")
                print(f"Error: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")


# Example usage


    


    def update_theme_liquid(self,theme_id, updated_liquid,shop):
        url = f"https://{shop.shop_name}/admin/api/2023-10/themes/{theme_id}/assets.json"
        headers = {
            "X-Shopify-Access-Token": shop.access_token,
            "Content-Type": "application/json"
        }
        data = {
            "asset": {
                "key": "layout/theme.liquid",
                "value": updated_liquid
            }
        }

        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print("Successfully updated theme.liquid")
        else:
            print("Error updating theme.liquid:", response.status_code, response.text)
    def upload_app_block_to_theme(self,shop,version):
        # Initialize the Shopify session (use correct API version and access token)
        session = shopify.Session(shop.shop_name, version, shop.access_token)
        shopify.ShopifyResource.activate_session(session)
        
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
            print(main_theme)
        
        else:
            raise Exception(f"Error fetching themes: {response.status_code}")
        if not main_theme:
            raise Exception("No main theme found")
        theme_id = main_theme[0]["id"]  

        print(main_theme)

    #     url = f"https://{shop.shop_name}/admin/api/2024-10/themes/{theme_id}/assets.json"

    #     headers = {
    #     "X-Shopify-Access-Token": shop.access_token,
    #     "Content-Type": "application/json"
    # }
    #     params = {"asset[key]": "layout/theme.liquid"}

    #     response = requests.get(url, headers=headers, params=params)
    
    #     if response.status_code == 200:
    #         theme_content = response.json().get("asset", {}).get("value")
    #         print("Fetched theme.liquid content")
    #         if theme_content:
    #             script_to_add = """
    #             <script>
    #             console.log("Custom script injected via Python");
    #             </script>
    #             """
    #             updated_liquid = theme_content.replace("</body>", script_to_add + "\n</body>")
                
    #             # Update the `theme.liquid`
    #             self.update_theme_liquid(theme_id, updated_liquid,shop)
    #     else:
    #         print("Error fetching theme.liquid:", response.status_code, response.text)
            
     

        # Snippet content
        # snippet_name = "layout/theme.liquid"
        # snippet_content = '''<div class="customer-info">Welcome, {{ customer.first_name }} {{ customer.id }}</div>'''
        # GRAPHQL_URL = f'https://{shop.shop_name}/admin/api/{version}/graphql.json'
        # Define the API URL and the necessary headers


#         # Define the URL and access token
#         url = f'https://{shop.shop_name}/admin/api/2024-10/graphql.json'
#         # Define the GraphQL query
#         query = """
# {
#   customers(first: 10, query: "state:'ENABLED'") {
#     edges {
#       node {
#         id
#         state
#       }
#     }
#   }
# }
# """

#         print(shop.access_token)

#         # Set up the headers for the request
#         headers = {
#             'Content-Type': 'application/json',
#             'X-Shopify-Access-Token': shop.access_token
#         }

#         # Send the POST request
#         response = requests.post(url, headers=headers, data=query)

#         # Check if the request was successful and print the response
#         if response.status_code == 200:
#             data = response.json()
#             print(json.dumps(data, indent=2))  # Print the formatted JSON response
#         else:
#             print(f"Error: {response.status_code}, {response.text}")

















        theme_id = f"gid://shopify/OnlineStoreTheme/{theme_id}"

        asset_key = "layout/theme.liquid"
        asset_value = """
            <script>
  console.log("Customer object:", {{ customer | json }});
</script>
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
        files = [
            {
                "filename": asset_key,
                "body": {
                    "type": 'TEXT',
                    "value": asset_value.strip()
                }
            }
        ]

        self.upsert_theme_files(shop.shop_name, shop.access_token, theme_id, files)

        

        # # Optionally, you can inject the app block into the theme's template or section
        # self.inject_app_block_to_theme(theme_id)

    # Function to inject the app block into the theme's template (optional)
    def inject_app_block_to_theme(self,theme_id):
        try:
            # Fetch the theme's template (you can specify a section or template like 'index.liquid')
            template = shopify.Asset.find(theme_id=theme_id, key='layout/theme.liquid')
            
            # Check if the template exists and inject the app block reference
            if template:
                updated_value = template.value + "\n{% include 'customer_info_block' %}"
                template.value = updated_value
                template.save()
                print("App block injected into theme.liquid")
            else:
                print("Template not found!")
        except Exception as e:
            print(f"Error injecting app block into theme: {e}")

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
                console.log("Custom script injected via Python");
                </script>
                """
                updated_liquid = theme_content.replace("</body>", script_to_add + "\n</body>")
                self.update_theme_liquid(theme_id, updated_liquid, shop,version)
            else:
                print("Error: theme.liquid content is empty.")
        else:
            print(f"Error fetching theme.liquid: {response.status_code}, {response.text}")

    def update_theme_liquid(self, theme_id, updated_content, shop,version):
        # Update the theme.liquid file with the new content
        url = f"https://{shop.shop_name}/admin/api/{version}/themes/{theme_id}/assets.json"
        headers = {
            "X-Shopify-Access-Token": shop.access_token,
            "Content-Type": "application/json"
        }
        data = {
            "asset": {
                "key": "layout/theme.liquid",  # Ensure this matches the asset key for theme.liquid
                "value": updated_content
            }
        }

        updated_liquid = """
<script>
console.log("Customer object:", {{ customer | json }});
</script>
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
"""  # Inject your script here

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            assets = response.json().get('assets', [])
            theme_liquid_exists = any(asset['key'] == 'layout/theme.liquid' for asset in assets)
            print(f"theme.liquid exists: {theme_liquid_exists}")
            self.update_theme_liquid_graphql(shop, theme_id, updated_liquid)

            # response = requests.put(url, headers=headers, json=data)
            # print(response.headers.get('X-Shopify-Shop-Api-Call-Limit'))
            # if response.status_code == 200:
            #     print("Successfully updated theme.liquid")
            #     return JsonResponse({"success": True, "message": "Successfully updated theme.liquid"}) 
            # else:
            #     print(f"Error updating theme.liquid: {response.status_code}, {response.text}")
            #     return JsonResponse({"success": False, "message": f"Error updating theme.liquid: {response.status_code}, {response.text}"})
        else:
            print(f"Error fetching assets: {response.status_code}, {response.text}")

    def update_theme_liquid_graphql(self,shop, theme_id, updated_liquid):
        url = f"https://{shop.shop_name}/admin/api/2024-10/graphql.json"
        # GraphQL mutation query and variables
        query = """
        mutation themeFilesUpsert($files: [OnlineStoreThemeFilesUpsertFileInput!]!, $themeId: ID!) {
  themeFilesUpsert(files: $files, themeId: $themeId) {
    upsertedThemeFiles {
      filename
    }
    userErrors {
      field
      message
    }
  }
}
        """

        variables = {
            "themeId": f"gid://shopify/OnlineStoreTheme/{theme_id}",
            "files": [
    {
      "filename": "layout/theme.liquid",
      "body": {
        "type": "TEXT",
        "value": updated_liquid
      }
    }
  ]
        }

        payload = {
            "query": query,
            "variables": variables
        }
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": shop.access_token,
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if "errors" in result:
                    print("Errors returned by Shopify API:")
                    print(json.dumps(result["errors"], indent=4))
                else:
                    print("Theme files upserted successfully:")
                    print(json.dumps(result, indent=4))
            else:
                print(f"Failed to upsert theme files. Status Code: {response.status_code}")
                print(f"Error: {response.text}")   
        except requests.exceptions.RequestException as e:
                    print(f"Request error: {e}")