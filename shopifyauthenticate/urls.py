from django.urls import path
from . import views

urlpatterns = [
    path('auth/callback/', views.shopify_callback, name='shopify_callback'),
]