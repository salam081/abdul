# Generated by Django 5.1.6 on 2025-07-08 05:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consumable', '0002_item_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='consumablerequest',
            name='file_payslpt',
            field=models.ImageField(blank=True, null=True, upload_to='file_payslpt'),
        ),
    ]
