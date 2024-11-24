from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('csrf/', views.csrf, name='csrf'),
    path('shopify/product-recommendations/', views.ProductRecommendationView.as_view(), name='product-recommendations'),
    path('track-activity/', views.TrackActivityView.as_view(), name='track-activity'),
]