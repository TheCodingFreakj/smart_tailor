from django.db import models

class ShopifyStore(models.Model):
    shop_name = models.CharField(max_length=255, unique=True)  # Shopify store URL (e.g., 'myshop.myshopify.com')
    access_token = models.CharField(max_length=255)  # Access token for Shopify API authentication
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the record was created
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp when the record was last updated
    is_installed = models.BooleanField(default=False)
    first_time = models.BooleanField(default=True)
    referer = models.CharField(max_length=255,default='https://admin.shopify.com/')
    

    def __str__(self):
        return f"{self.shop_name} - {self.access_token[:10]}..."  # Truncate the token for display
