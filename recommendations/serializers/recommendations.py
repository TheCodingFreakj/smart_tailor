from rest_framework import serializers
from ..models import SliderSettings

class SliderSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SliderSettings
        fields = ['customer', 'settings']

