from rest_framework import serializers
from .models import ItemReport, ItemCategory, ItemPhoto, Claim, Notification


class ItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCategory
        fields = ['id', 'name', 'slug', 'icon']


class ItemPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemPhoto
        fields = ['id', 'image', 'caption']


class ItemReportSerializer(serializers.ModelSerializer):
    photos = ItemPhotoSerializer(many=True, read_only=True)
    category = ItemCategorySerializer(read_only=True)
    reporter_name = serializers.CharField(source='reporter.get_full_name', read_only=True)
    
    class Meta:
        model = ItemReport
        fields = [
            'id', 'title', 'description', 'type', 'status', 
            'category', 'location_text', 'date_event', 
            'reward_offered', 'created_at', 'photos', 
            'reporter_name', 'view_count'
        ]


class ClaimSerializer(serializers.ModelSerializer):
    report = ItemReportSerializer(read_only=True)
    
    class Meta:
        model = Claim
        fields = ['id', 'report', 'message', 'status', 'created_at', 'resolved_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'verb', 'is_read', 'created_at']