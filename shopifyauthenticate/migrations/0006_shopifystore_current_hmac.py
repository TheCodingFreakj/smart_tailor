# Generated by Django 5.1.3 on 2024-11-23 05:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shopifyauthenticate', '0005_shopifystore_referer'),
    ]

    operations = [
        migrations.AddField(
            model_name='shopifystore',
            name='current_hmac',
            field=models.CharField(default='', max_length=255, unique=True),
        ),
    ]