from rest_framework import serializers
from ..models import ProductRecommendation, SliderSettings,ActiveUser

class SliderSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SliderSettings
        fields = ['customer', 'settings','renderedhtml']

class ProductRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRecommendation
        fields = ['product_id', 'recommendation_score', 'timestamp', 'last_updated', 'product_name', 'customer_id', 'loggedin_customer_id']





class ActiveUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActiveUser
        fields = ['customer_id', 'shop', 'is_active', 'added_at', 'updated_at']