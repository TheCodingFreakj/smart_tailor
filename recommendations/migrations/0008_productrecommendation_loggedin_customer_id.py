# Generated by Django 5.1.3 on 2024-11-30 21:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recommendations', '0007_productrecommendation_customer_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='productrecommendation',
            name='loggedin_customer_id',
            field=models.CharField(default='', max_length=255),
        ),
    ]
