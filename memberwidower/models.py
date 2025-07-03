from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal
from accounts.models import Member, User
from financialsummary.models import FinancialSummary
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from financialsummary.models import FinancialSummary
from main.models import Savings, Interest, Loanable, Investment


class Withdrawal(models.Model):
    STATUS_CHOICES = [ ('Pending', 'Pending'),('Approved', 'Approved'), ('Declined', 'Declined'),]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='withdrawal_requests')
    reason = models.TextField(blank=True, null=True)
    date_requested = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_withdrawals')
    date_approved = models.DateTimeField(null=True, blank=True)

    # Track the amounts at the time of withdrawal for record keeping
    withdrawn_savings = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    withdrawn_loanable = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    withdrawn_investment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.member} - {self.status}"
    
   
    def approve(self, admin_user):
        from main.models import Savings, Loanable, Investment
        from django.utils import timezone

        with transaction.atomic():
            # Get total savings
            total_savings = Savings.objects.filter(member=self.member).aggregate(
                total=models.Sum('month_saving')
            )['total'] or Decimal('0.00')

            # Get available loanable and investment
            total_loanable = Loanable.objects.filter(member=self.member).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')

            total_investment = Investment.objects.filter(member=self.member).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')

            # Calculate how much to remove from each (match withdrawn_savings)
            loanable_to_withdraw = min(total_savings, total_loanable)
            investment_to_withdraw = min(total_savings, total_investment)

            # Track what was withdrawn
            self.withdrawn_savings = total_savings
            self.withdrawn_loanable = loanable_to_withdraw
            self.withdrawn_investment = investment_to_withdraw
            self.total_withdrawn = total_savings  # Only savings is paid out

            self.status = "Approved"
            self.date_approved = timezone.now()
            self.approved_by = admin_user
            self.save()

            # Delete savings records and update member total
            Savings.objects.filter(member=self.member).delete()
            self.member.total_savings = Decimal('0.00')
            self.member.save()

            # Reduce loanable and investment accordingly
            Loanable.objects.filter(member=self.member).delete()
            Investment.objects.filter(member=self.member).delete()


    def decline(self, admin_user, reason=None):
        from django.utils import timezone
        from django.db import transaction

        with transaction.atomic():
            self.status = "Declined"
            self.date_approved = timezone.now()
            self.approved_by = admin_user
            self.save()


    def get_member_financial_summary(self):
        """Get complete financial summary for the member"""
        from .models import Savings, Interest, Loanable, Investment

        total_savings = Savings.objects.filter(member=self.member).aggregate(
            total=models.Sum('month_saving')
        )['total'] or Decimal('0.00')

        total_interest = Interest.objects.filter(member=self.member).aggregate(
            total=models.Sum('amount_deducted')
        )['total'] or Decimal('0.00')

        total_loanable = Loanable.objects.filter(member=self.member).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        total_investment = Investment.objects.filter(member=self.member).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        return {
            'total_savings': total_savings,
            'total_interest': total_interest,
            'total_loanable': total_loanable,
            'total_investment': total_investment,
            'grand_total': total_savings  # ONLY savings considered withdrawn
        }






