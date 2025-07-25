# Generated by Django 5.1.6 on 2025-07-21 15:46

import django.db.models.deletion
import loan.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BankName',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='BankCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('bank_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='loan.bankname')),
            ],
            options={
                'unique_together': {('bank_name', 'name')},
            },
        ),
        migrations.CreateModel(
            name='LoanRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('approved_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('loan_term_months', models.PositiveIntegerField()),
                ('application_date', models.DateField(default=loan.models.today_date)),
                ('approval_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('paid', 'paid')], default='pending', max_length=20)),
                ('rejection_reason', models.TextField(blank=True, null=True)),
                ('file_one', models.ImageField(blank=True, null=True, upload_to='file_one')),
                ('account_number', models.CharField(max_length=100)),
                ('guarantor_accepted', models.BooleanField(default=False)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_loan', to=settings.AUTH_USER_MODEL)),
                ('bank_code', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='loan.bankcode')),
                ('bank_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='loan.bankname')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('guarantor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='guaranteed_loans', to='accounts.member')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loan_requests', to='accounts.member')),
            ],
        ),
        migrations.CreateModel(
            name='LoanRepayback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('repayment_date', models.DateField()),
                ('amount_paid', models.DecimalField(decimal_places=2, max_digits=10)),
                ('balance_remaining', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('loan_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repaybacks', to='loan.loanrequest')),
            ],
        ),
        migrations.CreateModel(
            name='LoanRequestFee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('form_fee', models.DecimalField(decimal_places=2, max_digits=10)),
                ('loan_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.member')),
            ],
        ),
        migrations.CreateModel(
            name='LoanSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('allow_loan_requests', models.BooleanField(default=True)),
                ('allow_consumable_requests', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='LoanType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
                ('max_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('max_loan_term_months', models.PositiveIntegerField(blank=True, null=True)),
                ('available', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='loanrequest',
            name='loan_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='loan.loantype'),
        ),
    ]
