from rest_framework import serializers
from ..models import ProductRecommendation, SliderSettings

class SliderSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SliderSettings
        fields = ['customer', 'settings','renderedhtml']

class ProductRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRecommendation
        fields = ['product_id', 'recommendation_score', 'timestamp', 'last_updated', 'product_name', 'customer_id', 'loggedin_customer_id']