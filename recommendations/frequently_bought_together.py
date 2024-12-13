import requests
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from datetime import datetime
from .models import ProductOftenBoughtTogether  

class ProductRecommendationManager:
    def __init__(self, shop, api_version):
        self.shop = shop
        self.api_version = api_version

    def fetch_often_bought_together(self, activity_data):
        params = {
            "customer_id": activity_data["customerId"]
        }
        url = f"https://{self.shop.shop_name}/admin/api/{self.api_version}/orders.json"
        headers = {
            "X-Shopify-Access-Token": self.shop.access_token,
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers, params=params)

        # Step 1: Extract product details
        orders_data = []
        for order in response.json().get("orders", []):
            order_number = order["order_number"]
            products = [
                {"product_id": item["product_id"], "quantity": item["quantity"]}
                for item in order["line_items"]
            ]
            orders_data.append({"order_number": order_number, "line_items": products})

        # Step 2: Extract unique product IDs
        product_ids = set()
        for order in orders_data:
            for item in order['line_items']:
                product_ids.add(item['product_id'])

        # Step 3: Create a list of transactions (each transaction is a list of product IDs bought)
        transactions = []
        for order in orders_data:
            transaction = [item['product_id'] for item in order['line_items']]
            transactions.append(transaction)

        # Convert the transaction data into the format for mlxtend
        te = TransactionEncoder()
        te_ary = te.fit(transactions).transform(transactions)

        # Convert the array to a DataFrame
        df = pd.DataFrame(te_ary, columns=te.columns_)

        # Step 4: Apply the Apriori algorithm
        frequent_itemsets = apriori(df, min_support=0.005, use_colnames=True)

        # Generate association rules with the 'num_itemsets' argument
        num_items = len(df.columns)
        rules = association_rules(frequent_itemsets, num_itemsets=num_items, metric="lift", min_threshold=0.1)

        # Filter by more lenient thresholds
        filtered_rules = rules[
            (rules['confidence'] >= 0.5) & (rules['lift'] >= 0.5) & (rules['support'] >= 0.1)
        ]

        # Recommend products
        recommended = self.recommend_products(activity_data["product_id"], filtered_rules)
        self.add_or_update_recommendation(activity_data["customerId"], activity_data["product_id"], recommended)

    def add_or_update_recommendation(self, customer_id, product_id, recommended_products, notes='Frequently bought together based on past purchases.'):
        obj, created = ProductOftenBoughtTogether.objects.update_or_create(
            customer_id=customer_id,
            product_id=product_id,
            defaults={
                "recommended_products": recommended_products,
                "updated_at": datetime.now(),
                "notes": notes,
            }
        )
        if created:
            print(f"Created new recommendation for Product {product_id} and Customer {customer_id}.")
        else:
            print(f"Updated existing recommendation for Product {product_id} and Customer {customer_id}.")

    def recommend_products(self, product_id, rules, min_support=0.1, min_confidence=0.5, top_n=5):
        # Convert product_id to string to ensure uniformity
        product_id_str = str(product_id)
        
        # Filter rules where the product is in either antecedents or consequents
        relevant_rules = rules[
            (rules['antecedents'].apply(lambda x: product_id_str in map(str, x))) |
            (rules['consequents'].apply(lambda x: product_id_str in map(str, x)))
        ]
        
        # Filter further based on minimum support and confidence
        filtered_rules = relevant_rules[
            (relevant_rules['support'] >= min_support) & (relevant_rules['confidence'] >= min_confidence)
        ]
        
        # Extract consequents for the filtered rules
        recommendations = set()
        for consequents in filtered_rules['consequents']:
            recommendations.update(map(str, consequents))
        
        # Remove the product itself from recommendations
        recommendations.discard(product_id_str)
        
        # Convert recommendations to a list and limit to top_n recommendations
        recommendations = list(recommendations)
        recommendations = recommendations[:top_n]
        
        return recommendations
