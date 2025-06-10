from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from dateutil.relativedelta import relativedelta  
from datetime import date
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.db import transaction
from decimal import Decimal
from django.urls import reverse 
from django.contrib import messages
from django.db.models import Prefetch
from django.utils import timezone
import datetime
from django.http import JsonResponse
from datetime import date
from datetime import datetime
from main.models import *
from loan.models import *
from accounts.models import *
from consumable.models import *
from consumable.models import *
from .models import *







@login_required
def member_dashboard(request):
    try:
        member = Member.objects.get(member=request.user)
    except Member.DoesNotExist:
        return redirect('login')
    
    pending_guarantor_loans = LoanRequest.objects.filter(
        guarantor=member,
        guarantor_accepted=False,
        status="pending"
    )
    loanable_total = Loanable.objects.filter(member=member).aggregate(
        total=Sum('amount')
    )['total'] or 0

    investment_total = Investment.objects.filter(member=member).aggregate(
        total=Sum('amount')
    )['total'] or 0

    today = date.today()
    current_month = today.month
    current_year = today.year

    first_day_of_current_month = date(current_year, current_month, 1)
    previous_month_date = first_day_of_current_month - relativedelta(months=4)
    previous_month = previous_month_date.month
    previous_year = previous_month_date.year

    monthly_saving = Savings.objects.filter(
        member=member, 
        month__month=current_month, 
        month__year=current_year
    ).first()

    previous_monthly_saving = Savings.objects.filter(
        member=member, 
        month__month=previous_month, 
        month__year=previous_year
    ).first()

    # Prefer approved loan, fallback to rejected if none
    active_loan = LoanRequest.objects.filter(
        member=member, 
        status='approved'
    ).order_by('-approval_date').first()
    if not active_loan:
        active_loan = LoanRequest.objects.filter(
            member=member, 
            status='rejected'
        ).order_by('-approval_date').first()

    loan_paid = loan_balance = monthly_payment = 0
    if active_loan and active_loan.status == 'approved':
        repaybacks = LoanRepayback.objects.filter(loan_request=active_loan)
        loan_paid = repaybacks.aggregate(total=Sum('amount_paid'))['total'] or 0
        loan_balance = active_loan.approved_amount - loan_paid
        monthly_payment = active_loan.monthly_payment
        print(monthly_payment,monthly_payment)
    loan_types = LoanType.objects.all()
    consumable_requests = ConsumableRequest.objects.filter(user=request.user) \
        .prefetch_related('details__item') \
        .order_by('-date_created')[:5]

    approved_consumable = ConsumableRequest.objects.filter(user=request.user, status='Approved') \
        .order_by('-date_created')

    total_remaining = 0
    consumable_data = []

    for consumable in approved_consumable:
        approved_amount = consumable.calculate_total_price()
        total_paid = consumable.total_paid()
        balance = approved_amount - total_paid
        total_remaining += balance
        
        if consumable.details.exists():
            loan_term_months = consumable.details.first().loan_term_months
        else:
            loan_term_months = 1
        
        monthly_payment = approved_amount / loan_term_months

        consumable_data.append({ 
            'consumable': consumable,
            'approved_amount': approved_amount,
            'total_paid': total_paid,
            'balance': balance,
            'monthly_payment': monthly_payment,
        })

    context = {
        'member': member,
        'total_savings': member.total_savings or 0,
        'monthly_saving': monthly_saving.month_saving if monthly_saving else 0,
        'previous_monthly_saving': previous_monthly_saving.month_saving if previous_monthly_saving else 0,
        'loan': active_loan,
        'loan_paid': loan_paid,
        'loan_balance': loan_balance,
        'monthly_payment': monthly_payment,
        'loan_types': loan_types,
        'consumable_requests': consumable_requests,
        'approved_consumable': consumable_data,
        'loanable_total': loanable_total,
        'investment_total': investment_total,
        'approved_consumable': consumable_data,
        'total_remaining': total_remaining,
        "pending_guarantor_loans": pending_guarantor_loans
    }

    return render(request, 'member/dashboard.html', context)



@login_required
def disabled_requests_page(request):
    return render(request, 'member/disabled_requests.html', {
        'message': "Loan or consumable requests are currently Not Available. Please check back later."
    })



def ajax_load_bank_code(request):
    bank_id = request.GET.get('bank_id')
    try:
        bank_code = BankCode.objects.filter(bank_name_id=bank_id).first()
        return JsonResponse({'code': bank_code.name if bank_code else ''})
    except:
        return JsonResponse({'code': ''})

@login_required
def loan_request_view(request):
    settings = LoanSettings.objects.first()
    if not settings or not settings.allow_loan_requests:
        return render(request, "member/loan_request.html", {
            "loan_types": LoanType.objects.all(),
            "bank_names": BankName.objects.all(),
        })
    current_month = datetime.now().strftime('%b')
    member = getattr(request.user, 'member', None)
    if not member:
        messages.error(request, "You must be a registered member to request a loan.")
        return redirect("dashboard")

    # loan_types = LoanType.objects.all()
    loan_types = LoanType.objects.filter(name__icontains=current_month)
    bank_names = BankName.objects.all()

    if request.method == "POST":
        loan_type_id = request.POST.get('loan_type')
        amount = request.POST.get('amount')
        loan_term_months = request.POST.get('loan_term_months')
        file_one = request.FILES.get('file_one')
        bank_name_id = request.POST.get('bank_name')
        bank_code_id = request.POST.get('bank_code')
        account_number = request.POST.get('account_number')
        guarantor_ippis = request.POST.get('guarantor_ippis')
        # form_fee = request.POST.get('form_fee')

        # Validate loan type
        try:
            selected_loan_type = LoanType.objects.get(id=loan_type_id)
        except LoanType.DoesNotExist:
            messages.error(request, "Invalid loan type selected.")
            return redirect('loan_request')

        selected_type_name = selected_loan_type.name.lower()

        # Check active loans
        active_loans = LoanRequest.objects.filter(
            member=member,
            status__in=['pending', 'approved']
        ).select_related('loan_type')

        has_active_short = any('short term' in loan.loan_type.name.lower() for loan in active_loans)
        has_active_long = any('long term' in loan.loan_type.name.lower() for loan in active_loans)

        # Validation rules
        if 'short term' in selected_type_name and (has_active_short or has_active_long):
            messages.error(request, "You cannot request a SHORT TERM loan while you have an active Short or Long Term loan.")
            return redirect('loan_request')

        if 'long term' in selected_type_name and has_active_long:
            messages.error(request, "You cannot request a LONG TERM loan while you have an active Long Term loan.")
            return redirect('loan_request')

        # Guarantor validation
        try:
            guarantor_member = Member.objects.get(ippis=guarantor_ippis)
        except Member.DoesNotExist:
            messages.error(request, "Guarantor IPPIS is not registered.")
            return redirect('loan_request')

        if guarantor_member == member:
            messages.error(request, "You cannot be your own guarantor.")
            return redirect('loan_request')

        # Create the loan request
        LoanRequest.objects.create(
            member=member,
            loan_type=selected_loan_type,
            amount=amount,
            loan_term_months=loan_term_months,
            approved_amount=None,
            file_one=file_one,
            bank_name_id=bank_name_id,
            bank_code_id=bank_code_id,
            account_number=account_number,
            guarantor=guarantor_member,
            created_by=request.user,
        )
        # LoanFormFee.objects.create(form_fee = '500',paid_by=request.user,)
        
        messages.success(request, "Loan request submitted successfully!")
        return redirect('loan_request')

    context = {
        "loan_types": loan_types,
        "bank_names": bank_names,
        "settings": settings,
    }
    return render(request, "member/loan_request.html", context)


# def loan_request_view(request):
#     settings = LoanSettings.objects.first()
#     if not settings or not settings.allow_loan_requests:
#         return render(request, "member/loan_request.html", {
#             "loan_types": LoanType.objects.all(),
#             "bank_names": BankName.objects.all(),
#         })

#     current_month = datetime.now().strftime('%b')
#     member = getattr(request.user, 'member', None)
#     if not member:
#         messages.error(request, "You must be a registered member to request a loan.")
#         return redirect("dashboard")

#     loan_types = LoanType.objects.filter(name__icontains=current_month)
#     bank_names = BankName.objects.all()

#     if request.method == "POST":
#         loan_type_id = request.POST.get('loan_type')
#         amount = request.POST.get('amount')
#         loan_term_months = request.POST.get('loan_term_months')
#         file_one = request.FILES.get('file_one')

#         bank_name_id = request.POST.get('bank_name')
#         bank_code_id = request.POST.get('bank_code')
#         account_number = request.POST.get('account_number')

#         guarantor_ippis = request.POST.get('guarantor_ippis')

#         # Validate loan type
#         try:
#             loan_type = LoanType.objects.get(id=loan_type_id)
#         except (LoanType.DoesNotExist, ValueError, TypeError):
#             messages.error(request, "Please select a valid loan type.")
#             return redirect('loan_request')

#         # Check if member has an outstanding loan
#         has_outstanding_loan = LoanRequest.objects.filter(
#             member=member, loan_type=loan_type, status__in=['pending', 'approved']
#         ).exists()
#         if has_outstanding_loan:
#             messages.error(request, f"You already have an outstanding loan of type {loan_type.name}.")
#             return redirect('loan_request')

#         # Get guarantor from IPPIS
#         try:
#             guarantor_member = Member.objects.get(ippis=guarantor_ippis)
#         except Member.DoesNotExist:
#             messages.error(request, "The guarantor IPPIS does not belong to a registered member.")
#             return redirect('loan_request')

#         # Prevent self-guarantor
#         if guarantor_member == member:
#             messages.error(request, "You cannot be your own guarantor.")
#             return redirect('loan_request')

#         # Save the loan request
#         LoanRequest.objects.create(
#             member=member,
#             loan_type=loan_type,
#             amount=amount,
#             loan_term_months=loan_term_months,
#             approved_amount=None,
#             file_one=file_one,
#             bank_name_id=bank_name_id,
#             bank_code_id=bank_code_id,
#             account_number=account_number,
#             guarantor=guarantor_member,
#             created_by=request.user,
#         )

#         messages.success(request, "Loan request submitted successfully!")
#         return redirect('loan_request')

#     context = {
#         "loan_types": loan_types,
#         "bank_names": bank_names,
#         "settings": settings,
#     }
#     return render(request, "member/loan_request.html", context)

@login_required
def show_guarantor_approval(request, pk):
    loan = get_object_or_404(LoanRequest, pk=pk)

    # Get the Member object linked to the current user
    member = getattr(request.user, 'member', None)

    if not member:
        messages.error(request, "You must be a registered member to access this.")
        return redirect('member_dashboard')

    if loan.guarantor != member:
        messages.error(request, "You are not authorized to view this loan.")
        return redirect('member_dashboard')

    # Show approval page
    return render(request, 'member/guarantor.html', {'loan': loan})



@login_required
def confirm_guarantor_approval(request, pk):
    loan = get_object_or_404(LoanRequest, pk=pk)

    member = getattr(request.user, 'member', None)
    if not member or loan.guarantor != member:
        messages.error(request, "You are not authorized to approve this loan.")
        return redirect('member_dashboard')

    if loan.guarantor_accepted:
        messages.info(request, "You have already accepted this loan request.")
    else:
        loan.guarantor_accepted = True
        loan.save()
        messages.success(request, "You have successfully accepted the loan guarantee.")

    return redirect('member_dashboard')



@login_required
def member_request_consumable(request):
    settings = LoanSettings.objects.first()
    
    # Check if consumable requests are allowed
    if not settings or not settings.allow_consumable_requests:
        messages.warning(request, "Consumable requests are currently not available. Check back later.")
        return redirect('disabled_requests_page')
    user = request.user
    # Fetch available items
    items = Item.objects.filter(available=True)

    if request.method == 'POST':
        loan_term_months = request.POST.get('loan_term_months')
        file_payslpt = request.FILES.get('file_payslpt')

        
        # Validate loan term
        if not loan_term_months or not loan_term_months.isdigit() or int(loan_term_months) <= 0:
            messages.error(request, "Please provide a valid loan term in months.")
            # return render(request, 'consumables/member_request_consumable.html', {'items': items})
            return render(request, 'member/request_consumable.html', {'items': items})
        selected_items = []
        
        # Collect selected items and their quantities
        for item in items:
            quantity = request.POST.get(f'quantity_{item.id}')
            if quantity and quantity.isdigit() and int(quantity) > 0:
                selected_items.append({
                    'item': item,
                    'quantity': int(quantity),
                    'price': item.price
                })

        # Check if any item was selected
        if not selected_items:
            messages.error(request, "Please select at least one item and specify its quantity.")
            # return render(request, 'consumables/member_request_consumable.html', {'items': items})
            return render(request, 'member/request_consumable.html', {'items': items})
        # Create the ConsumableRequest and its details inside a transaction to ensure atomicity
        try:
            with transaction.atomic():
                # Create the consumable request
                consumable_request = ConsumableRequest.objects.create(
                    user=user,
                    date_created=timezone.now(),
                    status='Pending',
                    file_payslpt=file_payslpt
                )

                # Create ConsumableRequestDetail records
                for entry in selected_items:
                    ConsumableRequestDetail.objects.create(
                        request=consumable_request,
                        item=entry['item'],
                        quantity=entry['quantity'],
                        item_price=entry['price'],
                        loan_term_months=int(loan_term_months),
                        date_created=timezone.now()
                    )

            # Success message after creating the request
            messages.success(request, "Your consumable request has been submitted.")
            return redirect('member_dashboard')

        except Exception as e:
            # If an error occurs during request or detail creation, show an error message
            messages.error(request, f"An error occurred while processing your request: {e}")
            return render(request, 'consumables/member_request_consumable.html', {'items': items})

    # Render the form page
    return render(request, 'member/request_consumable.html', {'items': items})
    # return render(request, 'consumables/member_request_consumable.html', {'items': items})


def edit_consumable_request(request, request_id):
    user = request.user
    consumable_request = get_object_or_404(ConsumableRequest, id=request_id, user=user, status='Pending')

    # Fetch items and current details
    items = Item.objects.filter(available=True)
    details = ConsumableRequestDetail.objects.filter(request=consumable_request)

    if request.method == 'POST':
        loan_term_months = request.POST.get('loan_term_months')

        if not loan_term_months or not loan_term_months.isdigit() or int(loan_term_months) <= 0:
            messages.error(request, "Please provide a valid loan term.")
            return render(request, 'consumables/edit_request.html', {
                'items': items,
                'details': details,
                'request_obj': consumable_request
            })

        selected_items = []
        for item in items:
            quantity = request.POST.get(f'quantity_{item.id}')
            if quantity and quantity.isdigit() and int(quantity) > 0:
                selected_items.append({
                    'item': item,
                    'quantity': int(quantity),
                    'price': item.price
                })

        if not selected_items:
            messages.error(request, "Please select at least one item with quantity.")
            return render(request, 'consumables/edit_request.html', {
                'items': items,
                'details': details,
                'request_obj': consumable_request
            })

        try:
            with transaction.atomic():
                # Delete old details
                ConsumableRequestDetail.objects.filter(request=consumable_request).delete()

                # Add updated details
                for entry in selected_items:
                    ConsumableRequestDetail.objects.create(
                        request=consumable_request,
                        item=entry['item'],
                        quantity=entry['quantity'],
                        item_price=entry['price'],
                        loan_term_months=int(loan_term_months),
                        date_created=timezone.now()
                    )

            messages.success(request, "Your consumable request has been updated.")
            return redirect('member_dashboard')

        except Exception as e:
            messages.error(request, f"Error updating request: {e}")
            return render(request, 'consumables/edit_request.html', {
                'items': items,
                'details': details,
                'request_obj': consumable_request
            })

    # Pre-fill form on GET
    return render(request, 'consumables/edit_request.html', {'items': items,'details': details,'request_obj': consumable_request})

def member_savings(request):
    try:
        member = Member.objects.get(member=request.user)
    except Member.DoesNotExist:
        return redirect('login')
    savings = Savings.objects.filter(member=member)
    total_savings = Savings.objects.filter(member=member).aggregate(
        total=Sum('month_saving')
    )['total'] or 0

    investmentsavings = Investment.objects.filter(member=member)
    total_investment = Investment.objects.filter(member=member).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    loanable = Loanable.objects.filter(member=member)
    total_loanable = Loanable.objects.filter(member=member).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    g_total = total_investment + total_loanable 
    print(g_total)
    total = g_total /4
    print(total)
    context = {'savings': savings,'total_savings':total_savings,
               'investmentsavings':investmentsavings,
               'total_investment':total_investment,
               'loanable':loanable,
               'total_loanable':total_loanable,
               'total':total,
               }
    return render(request, 'member/member_savings.html', context)



def my_loan_requests(request):
    # Get the Member instance for the current user
    member = request.user.member  

    # Filter LoanRequests for this member
    loan_requests = LoanRequest.objects.filter(member=member).exclude(status='Rejected').order_by('-date_created')

    loan_data = []
    for loan in loan_requests:
        approved_amount = loan.approved_amount or 0
        total_paid = sum(repay.amount_paid for repay in loan.repaybacks.all())
        balance = approved_amount - total_paid
        monthly_payment = loan.monthly_payment or 0

        loan_data.append({
            'loan': loan,
            'approved_amount': approved_amount,
            'total_paid': total_paid,
            'balance': balance,
            'monthly_payment': monthly_payment,
        })

    return render(request, 'member/my_loan_requests.html', {'loan_data': loan_data})


@login_required
def member_loan_request_detail(request, request_id):
    """
    View to display details of a specific loan request
    """
    loan_request = get_object_or_404(
        LoanRequest.objects.prefetch_related('repaybacks'),
        id=request_id,
        member=request.user.member
    )

    total_paid = sum(repay.amount_paid for repay in loan_request.repaybacks.all())
    approved_amount = loan_request.approved_amount or 0
    balance = approved_amount - total_paid
    monthly_payment = loan_request.monthly_payment or 0

    context = {
        'loan_request': loan_request,
        'repaybacks': loan_request.repaybacks.all(),
        'approved_amount': approved_amount,
        'total_paid': total_paid,
        'balance': balance,
        'monthly_payment': monthly_payment,
    }

    return render(request, 'member/loan_request_detail.html', context)



@login_required
def my_consumable_requests(request):
    user = request.user
    requests = ConsumableRequest.objects.filter(
        user=user
    ).prefetch_related('details__item').exclude(status='Declined').order_by('-date_created')

    total_remaining = 0
    consumable_data = []

    for consumable in requests:
        approved_amount = consumable.calculate_total_price()
        total_paid = consumable.total_paid()
        balance = approved_amount - total_paid
        total_remaining += balance

        if consumable.details.exists():
            loan_term_months = consumable.details.first().loan_term_months
        else:
            loan_term_months = 1

        monthly_payment = approved_amount / loan_term_months

        consumable_data.append({
            'consumable': consumable,
            'approved_amount': approved_amount,
            'total_paid': total_paid,
            'balance': balance,
            'monthly_payment': monthly_payment,
        })

    context = {
        'requests': requests,
        'consumable_data': consumable_data,
        'total_remaining': total_remaining,

    }

    return render(request, 'member/my_requests.html', context)



@login_required
def consumable_request_detail(request, request_id):
    """
    View to display details of a specific consumable request
    """
    consumable_request = get_object_or_404(
        ConsumableRequest.objects.prefetch_related('details__item'),
        id=request_id,
        user=request.user
    )
    
    context = {
        'consumable_request': consumable_request,
        'request_details': consumable_request.details.all(),
        'total_amount': consumable_request.calculate_total_price(),
        'total_paid': consumable_request.total_paid(),
        'balance': consumable_request.balance(),
    }
    
    return render(request, 'member/consumable_request_detail.html', context)




@require_POST
@login_required
def cancel_consumable_request(request, request_id):
    try:
        consumable_request = get_object_or_404(ConsumableRequest, id=request_id, user=request.user,status='Pending')
        consumable_request.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})







