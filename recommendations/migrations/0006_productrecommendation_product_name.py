# Generated by Django 5.1.3 on 2024-11-30 19:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recommendations', '0005_productrecommendation_last_updated'),
    ]

    operations = [
        migrations.AddField(
            model_name='productrecommendation',
            name='product_name',
            field=models.CharField(default='', max_length=255),
        ),
    ]
