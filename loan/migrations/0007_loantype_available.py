# Generated by Django 5.1.6 on 2025-07-11 08:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loan', '0006_loanrequestfee_delete_loanrequetsfee'),
    ]

    operations = [
        migrations.AddField(
            model_name='loantype',
            name='available',
            field=models.BooleanField(default=True),
        ),
    ]
