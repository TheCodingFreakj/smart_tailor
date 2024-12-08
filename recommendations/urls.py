from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('csrf/', views.csrf, name='csrf'),
    path('shopify/product-recommendations/', views.ProductRecommendationView.as_view(), name='product-recommendations'),
    path('track-activity/', views.TrackActivityView.as_view(), name='track-activity'),
    # path('track-login/', views.track_customer_login, name='track-login'),
    path('shopify/add-customer-code/', views.ShopifyThemeUpdater.as_view(), name='add-customer-code'),
    path('generate_fake_data/', views.generate_fake_data, name='generate_fake_data'),
    path('slider-settings/', views.SliderSettingsView.as_view(), name='slider-settings'),
    path('dynamic-components-list/', views.DynamicComponentListView.as_view(), name='dynamic-components-list'),
    path('capture-content/', views.CaptureFrontendContentView.as_view(), name='capture-content'),
    path('products/', views.ProductsData.as_view(), name='products'),
]