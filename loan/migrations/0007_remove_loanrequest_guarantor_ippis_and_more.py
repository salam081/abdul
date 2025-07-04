# Generated by Django 5.1.6 on 2025-07-03 13:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_member_member'),
        ('loan', '0006_loanrequest_approved_by'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='loanrequest',
            name='guarantor_ippis',
        ),
        migrations.RemoveField(
            model_name='loanrequest',
            name='guarantor_name',
        ),
        migrations.RemoveField(
            model_name='loanrequest',
            name='guarantor_phone',
        ),
        migrations.AddField(
            model_name='loanrequest',
            name='guarantor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='guaranteed_loans', to='accounts.member'),
        ),
        migrations.AddField(
            model_name='loanrequest',
            name='guarantor_accepted',
            field=models.BooleanField(default=False),
        ),
    ]
