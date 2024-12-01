# serializers.py
from rest_framework import serializers
from ..models import DynamicComponent

class DynamicComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicComponent
        fields = ['id', 'components_json', 'title']
