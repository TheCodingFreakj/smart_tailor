# Generated by Django 5.1.3 on 2024-11-17 22:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shopifyauthenticate', '0003_shopifystore_first_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shopifystore',
            name='is_installed',
            field=models.BooleanField(default=False),
        ),
    ]
