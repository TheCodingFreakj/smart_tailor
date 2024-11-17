from django.urls import path
from .views import ShopifyInstallView, check_installation_status, ShopifyCallbackView, ShopifyUninstallWebhookView, shopify_callback

urlpatterns = [
    path('auth/callback/', shopify_callback, name='shopify_callback'),
    path("check-installation/", check_installation_status, name="check_installation_status"),
    path("shopify/install/", ShopifyInstallView.as_view(), name="shopify-install"),
    path("shopify/callback/", ShopifyCallbackView.as_view(), name="shopify-callback"),
    path("shopify/uninstall-webhook/", ShopifyUninstallWebhookView.as_view(), name="shopify-uninstall-webhook"),
]