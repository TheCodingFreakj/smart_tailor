# Generated by Django 5.1.3 on 2024-11-20 15:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shopifyauthenticate', '0004_alter_shopifystore_is_installed'),
    ]

    operations = [
        migrations.AddField(
            model_name='shopifystore',
            name='referer',
            field=models.CharField(default='https://admin.shopify.com/', max_length=255),
        ),
    ]
