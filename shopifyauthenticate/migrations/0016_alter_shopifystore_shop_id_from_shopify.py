# Generated by Django 5.1.3 on 2024-11-27 07:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shopifyauthenticate', '0015_shopifystore_shop_id_from_shopify'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shopifystore',
            name='shop_id_from_shopify',
            field=models.CharField(default='', max_length=255),
        ),
    ]