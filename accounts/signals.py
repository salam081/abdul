from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import Member
from financialsummary.models import FinancialSummary

@receiver(post_save, sender=Member)
def create_financial_summary(sender, instance, created, **kwargs):
    if created and instance.member:
        FinancialSummary.objects.get_or_create(user=instance.member)
