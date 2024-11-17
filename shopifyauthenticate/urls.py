from django.urls import path
from .views import ShopifyInstallView, ShopifyCallbackView, ShopifyUninstallWebhookView, shopify_callback

urlpatterns = [
    path('auth/callback/', shopify_callback, name='shopify_callback'),
    path("shopify/install/", ShopifyInstallView.as_view(), name="shopify-install"),
    path("shopify/callback/", ShopifyCallbackView.as_view(), name="shopify-callback"),
    path("shopify/uninstall-webhook/", ShopifyUninstallWebhookView.as_view(), name="shopify-uninstall-webhook"),
]