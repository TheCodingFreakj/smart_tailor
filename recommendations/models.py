from django.db import models
from django.db.models import JSONField
from django.utils.timezone import now
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






class ProductOftenBoughtTogether(models.Model):
    customer_id = models.CharField(max_length=20, help_text="Unique identifier for the customer.")
    product_id = models.CharField(max_length=20, help_text="Unique identifier for the main product.")
    recommended_products = models.JSONField(help_text="List of product IDs often bought together.")
    updated_at = models.DateTimeField(default=now, help_text="Timestamp of the last update.")
    notes = models.TextField(blank=True, null=True, help_text="Additional information or comments.")

    def __str__(self):
        return f"Recommendations for Product {self.product_id} (Customer {self.customer_id})"

    class Meta:
        verbose_name = "Often Bought Together Recommendation"
        verbose_name_plural = "Often Bought Together Recommendations"
        unique_together = ("customer_id", "product_id")
        ordering = ["-updated_at"]



from django.db import models
from django.utils.timezone import now


class ActiveUser(models.Model):
    customer_id = models.CharField(max_length=255, unique=True)
    shop = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Active User"
        verbose_name_plural = "Active Users"
        indexes = [
            models.Index(fields=['shop', 'is_active']),
        ]

    def __str__(self):
        return f"Active User: {self.customer_id} in {self.shop}"



