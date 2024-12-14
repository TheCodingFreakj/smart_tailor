from celery import shared_task
from shopifyauthenticate.models import ShopifyStore
from .frequently_bought_together import ProductRecommendationManager
from .related_products_user import ShopifySliderManager

@shared_task
def process_loggedin_user_data_1(user_activity_data,shop):
    # Your background task logic here
    print(f"Running background task1 with parameter: {user_activity_data}")
    shop = ShopifyStore.objects.filter(shop_name=shop).first()
    manager = ShopifySliderManager(shop,'2024-10',user_activity_data)
    manager.manage_slider()
    return f"Task with {user_activity_data['customerId']} completed"


@shared_task
def process_loggedin_user_data_2(user_activity_data):
    # Your background task logic here
    print(f"Running background task2 with parameter: {user_activity_data}")
    shop = ShopifyStore.objects.filter(shop_name=user_activity_data["shop"]).first()
    manager = ProductRecommendationManager(shop,'2024-10')
    manager.fetch_often_bought_together(user_activity_data)
    return f"Task with {user_activity_data['customerId']} completed"