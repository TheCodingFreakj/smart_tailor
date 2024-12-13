from datetime import datetime
import re
import pandas as pd
import pytz
import requests
from .models import ProductRecommendation
import json
import logging
from sklearn.metrics.pairwise import cosine_similarity
from django.core import serializers




# Configure the logger
logging.basicConfig(
    level=logging.DEBUG,  # Set the minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Log message format
    handlers=[
        
        logging.StreamHandler()        # Output logs to the console
    ]
)

# Create a logger instance
logger = logging.getLogger("AppLogger")

class ShopifyDataFetcher:
    def __init__(self, shop, version, activity_data):
        self.shop = shop
        self.version = version
        self.activity_data = activity_data
        self.base_url = f"https://{shop.shop_name}/admin/api/{version}/graphql.json"
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": shop.access_token
        }

    def execute_graphql_query(self, query, variables=None):
        """Helper function to make the GraphQL API request."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        response = requests.post(self.base_url, headers=self.headers, data=json.dumps(payload), verify=certifi.where())
        
        if response.status_code != 200:
            logger.error(f"GraphQL request failed with status code {response.status_code}")
            return None
        
        return response.json()

    def get_all_customers(self):
        """Fetch all enabled customers."""
        query = """
        {
            customers(first: 10) {
                edges {
                    node {
                        id
                        state
                    }
                }
            }
        }
        """
        customer_data = self.execute_graphql_query(query)
        if not customer_data:
            return []

        # Extract numeric customer IDs
        customers = [edge['node'] for edge in customer_data['data']['customers']['edges']]
        numeric_ids = [re.search(r'\d+', customer['id']).group() for customer in customers]
        return numeric_ids

    def get_customer_orders(self, customer_ids):
        """Fetch all orders related to the given customer IDs."""
        all_customer_interactions = []
        
        for customer_id in customer_ids:
            query = f"""
            {{
                orders(first: 10, query: "customer_id:{customer_id}") {{
                    edges {{
                        node {{
                            id
                            updatedAt
                            customer {{
                                id
                            }}
                            customerJourney {{
                                customerOrderIndex
                                daysToConversion
                                firstVisit {{
                                    source
                                }}
                                moments {{
                                    occurredAt
                                }}
                                lastVisit {{
                                    source
                                }}
                            }}
                            lineItems(first:5) {{
                                edges {{
                                    node {{
                                        name
                                        quantity
                                        product {{
                                            id
                                            category {{
                                                name
                                            }}
                                            title
                                            variants(first: 5) {{
                                                nodes {{
                                                    displayName
                                                    price
                                                }}
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
            """
            customer_interaction_data = self.execute_graphql_query(query)
            if customer_interaction_data:
                all_customer_interactions.append(customer_interaction_data)
        
        return all_customer_interactions

    def get_all_products(self):
        """Fetch all products in the store."""
        query = """
        query {
            products(first: 10, reverse: true) {
                edges {
                    node {
                        id
                        title
                    }
                }
            }
        }
        """
        product_data = self.execute_graphql_query(query)
        if not product_data:
            return []
        
        return [product['node']['title'] for product in product_data['data']['products']['edges']]

    def process_customer_data(self, customer_interactions):
        """Process and normalize customer interaction data."""
        customer_data = []

        for data in customer_interactions:
            orders = data.get("data", {}).get("orders", {}).get("edges", [])
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
                        "product_id": product["id"],
                        "logged_in_customer": self.activity_data["customerId"],
                        "product_name": product_data.get("name", "Unknown Product"),
                        "quantity": product_data.get("quantity") if product.get("quantity") else None,
                        "category": product["category"]["name"] if product.get("category") and "name" in product["category"] else None,
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
        return customer_data

    def analyze_data(self, customer_data):
        """Analyze the customer data to calculate relevant metrics."""
        df = pd.json_normalize(customer_data, record_path=['moments'], meta=[
            'customer_id', 'logged_in_customer', 'product_name', 'product_id', 'quantity', 
            'category', 'variants', 'order_index', 'days_to_conversion', 'first_visit_source', 
            'last_visit_source', 'order_updated_at'
        ])

        # Convert 'occurredAt' to datetime and handle empty variants
        df['occurredAt'] = pd.to_datetime(df['occurredAt'])
        df['product_price'] = df['variants'].apply(lambda x: float(x[0]['price']) if x else None)
        df['product_displayName'] = df['variants'].apply(lambda x: x[0]['displayName'] if x else None)

        now_utc = datetime.now(pytz.utc)
        df['days_since_last_purchase'] = (now_utc - df['occurredAt']).dt.days
        df['quantity'] = df['quantity'].apply(lambda x: x if x is not None else 1)

        # Total quantity purchased per product
        product_purchase_quantity = df.groupby('product_name')['quantity'].sum()

        # Total revenue per product
        df['total_revenue'] = df["quantity"] * df['product_price']
        product_revenue = df.groupby('product_name')['total_revenue'].sum()

        # Total spend per customer
        df['total_spent'] = df['quantity'] * df['product_price']
        customer_total_spent = df.groupby('customer_id')['total_spent'].sum()

        # Sort by total spend to find high-value customers
        high_value_customers = customer_total_spent.sort_values(ascending=False)

        # Log analysis results
        logger.debug(f"High-value customers: {high_value_customers}")
        logger.debug(f"Product purchase quantities: {product_purchase_quantity}")
        logger.debug(f"Product revenue: {product_revenue}")

        return high_value_customers, product_purchase_quantity, product_revenue, df

    def get_related_products_user(self):
        """Main function to fetch data and analyze customer interactions."""
        customer_ids = self.get_all_customers()
        all_customer_interactions = self.get_customer_orders(customer_ids)
        customer_data = self.process_customer_data(all_customer_interactions)
        high_value_customers, product_purchase_quantity, product_revenue,df = self.analyze_data(customer_data)
        self.recommend_products_based_on_similarity(df, high_value_customers)
        
        
    
    def recommend_products_based_on_similarity(self,df, high_value_customers):
        """
        Function to recommend products based on the cosine similarity of customers' purchasing behavior.
        """
        # Create a pivot table with customers as rows and products as columns
        pivot_table = df.pivot_table(index='customer_id', columns='product_name', values='quantity', aggfunc='sum', fill_value=0)

        # Calculate cosine similarity between customers
        cosine_sim = cosine_similarity(pivot_table)

        # Example: Find most similar customers to the first high-value customer
        target_customer_idx = 0  # Use the top high-value customer as target
        similar_customers = cosine_sim[target_customer_idx]

        # Create a DataFrame with similarity scores and customer IDs
        similarity_df = pd.DataFrame({
            'customer_id': pivot_table.index,
            'similarity_score': similar_customers
        })

        # Exclude self-similarity (1.0 score)
        similarity_df = similarity_df[similarity_df['customer_id'] != pivot_table.index[target_customer_idx]]

        # Sort by similarity score (descending)
        similarity_df_sorted = similarity_df.sort_values(by='similarity_score', ascending=False)

        # Display the top N similar customers (e.g., top 5)
        top_similar_customers = similarity_df_sorted.head(5)
        logger.debug(f"Top similar customers: {top_similar_customers}")

        # Get products purchased by these similar customers
        similar_customers_ids = top_similar_customers['customer_id'].tolist()
        recommended_products = df[df['customer_id'].isin(similar_customers_ids)]

        # Recommend top N products (e.g., most purchased)
        recommended_products = recommended_products.groupby('product_name').agg(
            product_id=('product_id', 'first'),
            quantity=('quantity', 'sum'),
            customer_id=('customer_id', 'first'),
            loggedin_customer=('logged_in_customer', 'first')
        ).sort_values('quantity', ascending=False)

        logger.debug(f"Recommended products: {recommended_products.head()}")

        # Extract top recommended product names
        product_names = recommended_products.head().index.tolist()

        # Assuming 'recommended_products' is your DataFrame
        recommended_products = pd.DataFrame(recommended_products.head(), index=product_names)

        # Store recommendations to the database (this would depend on your model logic)
        self.store_recommendations_from_df(recommended_products)

        # Retrieve recommendations from the database for the logged-in customer
        recommendations = ProductRecommendation.objects.filter(
            loggedin_customer_id=self.activity_data["customerId"]
        ).order_by('-recommendation_score')

        # Serialize the queryset
        recommendations_json = serializers.serialize('json', recommendations)

        # This is the JSON you can pass to the frontend
        logger.debug(f"Serialized recommendations: {recommendations_json}")

        # Parse the serialized JSON and extract relevant data
        extracted_data = []
        for entry in json.loads(recommendations_json):  # Parse the JSON string to Python objects
            if 'fields' in entry:
                fields = entry['fields']
                extracted_data.append({
                    "product_id": fields["product_id"],
                    "recommendation_score": fields["recommendation_score"],
                    "timestamp": fields["timestamp"],
                    "last_updated": fields["last_updated"],
                    "product_name": fields["product_name"],
                    "customer_id": fields["customer_id"],
                    "loggedin_customer_id": fields["loggedin_customer_id"]
                })
            else:
                logger.warning(f"Invalid entry format: {entry}")

        # Convert the extracted data to JSON
        json_output = extracted_data
        logger.debug(f"Extracted recommendation data: {json_output}")

        return json_output
    def store_recommendations_from_df(self,df):
        """
        Processes the DataFrame and stores or updates product recommendations in the database.
        
        :param df: A pandas DataFrame containing product recommendation data
        """
        for product_name,  row in df.iterrows():
            product_id = row['product_id']
            recommendation_score = row['quantity']
            customer_id = row['customer_id']
            loggedin_customer_id = row['loggedin_customer']
            
            
            try:
                # Try to get the existing recommendation
                recommendation = ProductRecommendation.objects.get(product_id=product_id)
                # Update the recommendation score if it exists
                recommendation.recommendation_score = recommendation_score
                recommendation.customer_id = customer_id
                recommendation.loggedin_customer_id = loggedin_customer_id
                recommendation.product_name = product_name  # Optionally update the product name
                recommendation.save()
                print(f"Updated recommendation for {product_name} ({product_id}) with score {recommendation_score}")
            except ProductRecommendation.DoesNotExist:
                # If the recommendation doesn't exist, create a new record
                recommendation = ProductRecommendation.objects.create(
                    product_id=product_id,
                    product_name=product_name,
                    recommendation_score=recommendation_score,
                    customer_id=customer_id,
                    loggedin_customer_id = loggedin_customer_id
                )
                print(f"Created new recommendation for {product_name} ({product_id}) with score {recommendation_score}")