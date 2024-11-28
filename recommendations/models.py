from django.db import models

class UserActivity(models.Model):
    user_id = models.CharField(max_length=255)  # Shopify customer ID or anonymous user ID
    product_id = models.CharField(max_length=255)  # Shopify product ID
    product_url = models.CharField(max_length=255, default='')
    action_type = models.CharField(max_length=50, choices=[('view', 'View'), ('add_to_cart', 'Add to Cart')])
    timestamp = models.DateTimeField(auto_now_add=True)



class ProductRelationship(models.Model):
    product_id = models.BigIntegerField(primary_key=True)
    related_product_ids = models.JSONField()  # Store related product IDs as a JSON array

    def __str__(self):
        return f"Product {self.product_id} related to {len(self.related_product_ids)} products"