from django.urls import path
from . import views, ShopifyInstallView, ShopifyCallbackView

urlpatterns = [
    path('auth/callback/', views.shopify_callback, name='shopify_callback'),
    path("shopify/install/", ShopifyInstallView.as_view(), name="shopify-install"),
    path("shopify/callback/", ShopifyCallbackView.as_view(), name="shopify-callback"),
]