from decimal import Decimal
from accounts.models import Member
from memberwidower.models import Withdrawal
from django.db import models

def get_cooperative_withdrawal_stats():
    total_requests = Withdrawal.objects.count()
    pending_requests = Withdrawal.objects.filter(status='Pending').count()
    approved_requests = Withdrawal.objects.filter(status='Approved').count()
    declined_requests = Withdrawal.objects.filter(status='Declined').count()

    total_withdrawn = Withdrawal.objects.filter(
        status='Approved',
        total_withdrawn__isnull=False
    ).aggregate(total=models.Sum('total_withdrawn'))['total'] or Decimal('0.00')

    return {
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'declined_requests': declined_requests,
        'total_withdrawn': total_withdrawn
    }

def get_members_eligible_for_withdrawal():
    eligible_members = Member.objects.filter(
        total_savings__gt=Decimal('0.00')
    ).exclude(
        withdrawal_requests__status='Pending'
    )
    return eligible_members
