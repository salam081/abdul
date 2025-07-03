from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Withdrawal
from accounts.models import Member
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.db.models import Sum
from decimal import Decimal
from main.models import Savings, Investment, Loanable

# @staff_member_required
from django.db.models import Sum
from decimal import Decimal
from financialsummary.models import FinancialSummary

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.timezone import now
from accounts.models import Member
from accounts.utils import get_cooperative_withdrawal_stats, get_members_eligible_for_withdrawal

from .models import Withdrawal
from django.utils import timezone

# from accounts.models import Member


def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
def list_withdrawal_requests(request):
    requests = Withdrawal.objects.select_related('member', 'approved_by').all()
    stats = get_cooperative_withdrawal_stats()
    return render(request, 'withdrawal/members/list_requests.html', {
        'requests': requests,
        'stats': stats,
    })


@login_required
def member_withdrawal_request(request):
    member = get_object_or_404(Member, member=request.user)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        if Withdrawal.objects.filter(member=member, status='Pending').exists():
            messages.warning(request, "You already have a pending request.")
        elif member.total_savings <= 0:
            messages.warning(request, "You are not eligible for withdrawal.")
        else:
            Withdrawal.objects.create(member=member, reason=reason)
            messages.success(request, "Withdrawal request submitted successfully.")
        return redirect('member_withdrawal_request')

    return render(request, 'withdrawal/members/withdrawal_request_form.html', {
        'member': member,
    })


@login_required
@user_passes_test(is_admin)
def approve_withdrawal_request(request, pk):
    withdrawal_request = get_object_or_404(Withdrawal, pk=pk, status='Pending')
    withdrawal_request.approve(request.user)
    messages.success(request, f"Request by {withdrawal_request.member} approved.")
    return redirect('list_withdrawal_requests')


@login_required
@user_passes_test(is_admin)
def decline_withdrawal_request(request, pk):
    withdrawal_request = get_object_or_404(Withdrawal, pk=pk, status='Pending')

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        withdrawal_request.status = 'Declined'
        withdrawal_request.date_approved = timezone.now()
        withdrawal_request.approved_by = request.user
        withdrawal_request.save()

        messages.warning(request, f"Request by {withdrawal_request.member} declined.")
        return redirect('list_withdrawal_requests')

    return render(request, 'withdrawal/members/decline_confirm.html', {
        'request_obj': withdrawal_request
    })



@login_required
@user_passes_test(is_admin)
def eligible_members_view(request):
    eligible_members = get_members_eligible_for_withdrawal()
    return render(request, 'withdrawal/members/eligible_members.html', {
        'eligible_members': eligible_members,
    })



@staff_member_required
def cooperative_summary(request):
    summary_totals = FinancialSummary.objects.aggregate(
        total_savings=Sum('total_savings'),
        total_interest=Sum('total_interest'),
        total_investment=Sum('total_investment'),
        total_loanable=Sum('total_loanable'),
        grand_total=Sum('grand_total'),
       
    )
   
    context = {
        "total_savings": summary_totals['total_savings'] or Decimal('0.00'),
        "total_investment": summary_totals['total_investment'] or Decimal('0.00'),
        "total_loanable": summary_totals['total_loanable'] or Decimal('0.00'),
        "grand_total": summary_totals['grand_total'] or Decimal('0.00'),
        
    }
    return render(request, "widower/admin/coop_summary.html", context)

