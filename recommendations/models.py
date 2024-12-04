from django.db import models
from django.db.models import JSONField
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
    
class ProductRecommendation(models.Model):
    product_id = models.CharField(max_length=255)  # Shopify product ID, e.g., gid://shopify/Product/8942110376191
    recommendation_score = models.IntegerField()  # Recommendation score (e.g., 9, 6, 4, etc.)
    timestamp = models.DateTimeField(auto_now_add=True)  # Store the time the recommendation was created
    last_updated = models.DateTimeField(auto_now=True)
    product_name = models.CharField(max_length=255, default='')
    customer_id = models.CharField(max_length=255, default='')
    loggedin_customer_id = models.CharField(max_length=255, default='')

    class Meta:
        unique_together = ('product_id',)  # Ensure that the product_id is unique

    def __str__(self):
        return f"Product {self.product_id} with score {self.recommendation_score}"


class SliderSettings(models.Model):
    customer = models.CharField(max_length=255, default='')
    settings = JSONField()  # Store settings as a JSON object
    renderedhtml = models.TextField(default='')  # Store HTML content

    def __str__(self):
        return f"Settings for {self.customer}"
    



class DynamicComponent(models.Model):
    # Field to store JSON data
    components_json = models.JSONField()
    title = models.CharField(max_length=255, default='')

    def __str__(self):
        return f"Dynamic Component - {self.id}"

    # Optional: You can add a method to return the JSON content if needed
    def get_components(self):
        return self.components_json
