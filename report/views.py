
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum,Min, Max, Count, Q, Avg , F ,ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from django.db.models.functions import TruncMonth, TruncYear,TruncWeek
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from collections import defaultdict
from django.db.models.functions import ExtractYear
from django.db.models.functions import ExtractMonth
from django.db import transaction
from decimal import Decimal
from django.contrib import messages
import json
from consumable.models import *
from accounts.models import User
import csv
from loan.models import *
from accounts.decorator import group_required

from datetime import date

# Create your views here.
def all_income(request):
    # Get filter parameters from GET request
  
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Build Q objects for filtering
    savings_filter = Q()
    loanrepayback_filter = Q()
    consumable_payback_filter = Q()
    loan_fee_filter = Q()
    interest_filter = Q()

    # Filter by year and month
  
    if date_from:
        savings_filter &= Q(month__gte=date_from)
        loanrepayback_filter &= Q(repayment_date__gte=date_from)
        consumable_payback_filter &= Q(repayment_date__gte=date_from)
        loan_fee_filter &= Q(created_at__gte=date_from)  # fixed
        interest_filter &= Q(month__gte=date_from)

    if date_to:
        savings_filter &= Q(month__lte=date_to)
        loanrepayback_filter &= Q(repayment_date__lte=date_to)
        consumable_payback_filter &= Q(repayment_date__lte=date_to)
        loan_fee_filter &= Q(created_at__lte=date_to)  # fixed
        interest_filter &= Q(month__lte=date_to)


    # Aggregations with filters
    total_loans_fee = LoanRequestFee.objects.filter(loan_fee_filter).aggregate(total=Sum('form_fee'))['total'] or 0
    total_savings = Savings.objects.filter(savings_filter).aggregate(total_savings=Sum('month_saving'))['total_savings'] or 0
    deducted_amount = Interest.objects.filter(interest_filter).aggregate(total_savings=Sum('amount_deducted'))['total_savings'] or 0
    payback_loans = LoanRepayback.objects.filter(loanrepayback_filter).aggregate(total=Sum('amount_paid'))['total'] or 0
    total_consumable_payback = PaybackConsumable.objects.filter(consumable_payback_filter).aggregate(total=Sum('amount_paid'))['total'] or 0

    income = sum([total_loans_fee,total_savings,deducted_amount, payback_loans, total_consumable_payback])
    

    filters_applied = any([ date_from, date_to])
    context = {
        'total_loans_fee': total_loans_fee,
        'total_savings': total_savings,
        'payback_loans': payback_loans,
        'deducted_amount': deducted_amount,
        'total_consumable_payback': total_consumable_payback,
        'income': income,
        'date_from': date_from,
        'date_to': date_to,
        'filters_applied':filters_applied
    }
    return render(request, "reports/all_income.html", context)




def admin_loan_reports(request):
    # Default to current month
    month = request.GET.get('month', timezone.now().strftime('%Y-%m'))
    year, month_num = month.split('-')
    


    loan_type_id = request.GET.get('loan_type')

    monthly_requests = LoanRequest.objects.filter(
        application_date__year=year,
        # application_date__month=month_num
    )

    if loan_type_id:
        monthly_requests = monthly_requests.filter(loan_type_id=loan_type_id)

    monthly_approvals = monthly_requests.filter(status='approved')
    monthly_rejections = monthly_requests.filter(status='rejected')

    
    monthly_repayments = LoanRepayback.objects.filter(
        repayment_date__year=year,
        # repayment_date__month=month_num

    )
    if loan_type_id:
        monthly_repayments = monthly_repayments.filter(loan_request__loan_type_id=loan_type_id)

    loan_type_stats = LoanType.objects.annotate(
        total_requests=Count('loanrequest'),
        total_approved=Count('loanrequest', filter=Q(loanrequest__status='approved')),
        total_amount=Sum('loanrequest__approved_amount', filter=Q(loanrequest__status='approved'))
    )

    context = {
        'selected_month': month,
        'selected_loan_type': int(loan_type_id) if loan_type_id else None,
        'monthly_requests': monthly_requests.count(),
        'monthly_approvals': monthly_approvals.count(),
        'monthly_rejections': monthly_rejections.count(),
        'monthly_approved_amount': monthly_approvals.aggregate(Sum('approved_amount'))['approved_amount__sum'] or 0,
        'monthly_repayments': monthly_repayments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0,
        'loan_type_stats': loan_type_stats,
        'loan_types': LoanType.objects.all(),  
    }
    return render(request, 'reports/reports.html', context)

def loan_request_report(request):
    # Initialize query set with all loan requests
    loan_requests = LoanRequest.objects.all().order_by('-date_created')

    # Initialize filters dictionary
    filters = {
        'status': request.GET.get('status', 'all'),
        'date_from': request.GET.get('date_from'),
        'date_to': request.GET.get('date_to'),
        'month': request.GET.get('month'),
        'loan_type': request.GET.get('loan_type'), 
    }

    # Apply filters
    if filters['status'] and filters['status'] != 'all':
        loan_requests = loan_requests.filter(status=filters['status'])

    if filters['date_from']:
        loan_requests = loan_requests.filter(application_date__gte=filters['date_from'])

    if filters['date_to']:
        loan_requests = loan_requests.filter(application_date__lte=filters['date_to'])

    if filters['month']:
        try:
            year, month = map(int, filters['month'].split('-'))
            loan_requests = loan_requests.filter(
                application_date__year=year,
                application_date__month=month
            )
        except ValueError:
            # Handle invalid month format if necessary
            pass

    # Apply loan_type filter
    if filters['loan_type']: # If a loan type is selected
        loan_requests = loan_requests.filter(loan_type__name=filters['loan_type'])


    # Annotate loan requests with total paid and balance
    # Coalesce handles cases where there are no repayments yet (sum would be None)
    loan_requests = loan_requests.annotate(
        total_paid=Coalesce(Sum('repaybacks__amount_paid'), 0.00, output_field=DecimalField()),
        balance=ExpressionWrapper(
            F('approved_amount') - Coalesce(Sum('repaybacks__amount_paid'), 0.00),
            output_field=DecimalField()
        ),
        total_price=Coalesce(F('approved_amount'), F('amount'), output_field=DecimalField())
    )

    # Calculate summary statistics
    summary = {
        'total_requests': loan_requests.count(),
        'total_value': loan_requests.aggregate(total_approved=Coalesce(Sum('approved_amount'), 0.00, output_field=DecimalField()))['total_approved'],
        'total_paid': loan_requests.aggregate(total_repaid=Coalesce(Sum('repaybacks__amount_paid'), 0.00, output_field=DecimalField()))['total_repaid'],
        'total_balance': loan_requests.aggregate(total_outstanding=Coalesce(Sum('balance'), 0.00, output_field=DecimalField()))['total_outstanding'],
        'pending_count': loan_requests.filter(status='pending').count(),
        'approved_count': loan_requests.filter(status='approved').count(),
        'paid_count': loan_requests.filter(status='paid').count(),
        'declined_count': loan_requests.filter(status='rejected').count(),
    }

    # Determine status choices for the filter dropdown
    status_choices = [('all', 'All Statuses')] + list(LoanRequest.status.field.choices)

    # Get unique months from existing loan requests for the "Filter by Month" dropdown
    distinct_application_dates = LoanRequest.objects.dates('application_date', 'month', order='DESC')
    months = [d for d in distinct_application_dates]

    # Get unique loan types for the "Filter by Loan Type" dropdown
    # Ensure LoanType model is imported as it's more direct to query LoanType itself
    # rather than LoanRequest.objects.values_list, which can miss loan types with no requests.
    # However, if you only want types that HAVE requests, your original line is fine.
    # Using LoanType.objects.all() to get all available loan types is generally more robust
    # for a filter dropdown.
    loan_types_qs = LoanType.objects.all().order_by("name")

    # Pagination
    page_number = request.GET.get('page')
    paginator = Paginator(loan_requests, 100) 
    page_obj = paginator.get_page(page_number)

    context = {
        'requests': page_obj,
        'summary': summary,
        'filters': filters,
        'status_choices': status_choices,
        'months': months,
        'loan_types': loan_types_qs, 
    }
    return render(request, 'reports/loan_request_report.html', context)



def filtered_loan_repayments(request):
    years = LoanRequest.objects.annotate(year=ExtractYear("application_date")) \
        .values_list("year", flat=True).distinct().order_by("-year")
    loan_types = LoanRequest.objects.values_list("loan_type__name", flat=True).distinct().order_by("loan_type__name")

    selected_year = request.GET.get("year")
    selected_type = request.GET.get("loan_type")

    filters = Q()
    if selected_year:
        filters &= Q(loan_request__application_date__year=selected_year)
    if selected_type:
        filters &= Q(loan_request__loan_type__name=selected_type)

    repayments_qs = LoanRepayback.objects.select_related("loan_request__member", "loan_request__loan_type") \
        .filter(filters).order_by("-repayment_date")
    # Sum total repayment amount across all filtered records
    total_sum_paid = repayments_qs.aggregate(Sum("amount_paid"))["amount_paid__sum"] or 0

    # Enrich each repayment with total paid and balance
    enriched_repayments = []
    total_sum_remaining = 0 
    for repay in repayments_qs:
        loan = repay.loan_request
        total_paid = LoanRepayback.objects.filter(loan_request=loan).aggregate(Sum("amount_paid"))["amount_paid__sum"] or 0
        approved = loan.approved_amount or 0
        balance = approved - total_paid
        total_sum_remaining += balance  

        enriched_repayments.append({
            "repayment": repay,"total_paid": total_paid,"balance_remaining": balance,})
        
    # Add pagination
    paginator = Paginator(enriched_repayments, 100) 
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {"page_obj": page_obj,"years": years, "loan_types": loan_types,
                "selected_year": selected_year, "selected_type": selected_type,
                "total_sum_paid": total_sum_paid,"total_sum_remaining": total_sum_remaining,}
    return render(request, "reports/filtered_loan_repayments.html", context)

@login_required
def request_status_report(request):
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    user_filter = request.GET.get('user')
    selected_month = request.GET.get('month')

    # Base queryset with optimized select_related and prefetch_related
    queryset = ConsumableRequest.objects.select_related(
        'user', 'approved_by'
    ).prefetch_related('details')

    # Apply filters
    if status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    # Date filtering with proper date parsing
    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
            queryset = queryset.filter(date_created__gte=date_from_parsed)
        except ValueError:
            pass  # Invalid date format, ignore filter

    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
            queryset = queryset.filter(date_created__lte=date_to_parsed)
        except ValueError:
            pass  # Invalid date format, ignore filter

    if user_filter:
        try:
            user_id = int(user_filter)
            queryset = queryset.filter(user_id=user_id)
        except (ValueError, TypeError):
            pass  # Invalid user ID, ignore filter

    # Month filtering - fixed to include month filter
    if selected_month:
        try:
            year, month = map(int, selected_month.split('-'))
            queryset = queryset.filter(
                date_created__year=year,
                date_created__month=month  # Uncommented this line
            )
        except ValueError:
            pass  # Invalid month format, ignore filter

    # Get list of months with requests (optimized)
    month_list = ConsumableRequest.objects.dates('date_created', 'month', order='DESC')

    # Order queryset for consistent results
    queryset = queryset.order_by('-date_created')

    # Build request data with optimized queries
    requests_data = []
    for req in queryset:
        requests_data.append({
            'id': req.id,
            'user': req.user.username,
            'date_created': req.date_created,
            'status': req.status,
            'approved_by': req.approved_by.username if req.approved_by else None,
            'total_price': req.calculate_total_price(),
            'total_paid': req.total_paid(),
            'balance': req.balance(),
            'items_count': req.details.count()  # This will use prefetch_related
        })

    # Pagination
    paginator = Paginator(requests_data, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Summary with database aggregation for better performance
    summary_data = queryset.aggregate(
        total_requests=Count('id'),
        pending_count=Count('id', filter=Q(status='Pending')),
        approved_count=Count('id', filter=Q(status='Approved')),
        paid_count=Count('id', filter=Q(status='Paid')),
        declined_count=Count('id', filter=Q(status='Declined')),
    )

    # Calculate financial totals (these might need custom aggregation based on your model)
    total_value = sum(req.calculate_total_price() for req in queryset)
    total_paid = sum(req.total_paid() for req in queryset)
    total_balance = sum(req.balance() for req in queryset)

    summary = {
        **summary_data,
        'total_value': total_value,
        'total_paid': total_paid,
        'total_balance': total_balance,
    }

    # Get users who have made requests for the dropdown
    # users_with_requests = User.objects.filter(
    #     consumablerequest__isnull=False
    # ).distinct().order_by('username')

    context = {
        'requests': page_obj,'summary': summary,
       
        'months': month_list,
        'filters': {
            'status': status_filter,
            'date_from': date_from,
            'date_to': date_to,
            'user': user_filter,
            'month': selected_month,
        },
        'status_choices': [
            ('all', 'All Statuses'),
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Paid', 'Paid'),
            ('Declined', 'Declined'),
        ]
    }

    return render(request, 'reports/consumable_request_status_report.html', context)




@login_required
def user_spending_report(request):
    """Report showing spending patterns by user"""
    
    # Get date range filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    queryset = User.objects.all()
    
    user_spending = []
    for user in queryset:
        user_requests = ConsumableRequest.objects.filter(user=user)
        
        # Apply date filters
        if date_from:
            user_requests = user_requests.filter(date_created__gte=date_from)
        if date_to:
            user_requests = user_requests.filter(date_created__lte=date_to)
        
        total_requested = sum(req.calculate_total_price() for req in user_requests)
        total_paid = sum(req.total_paid() for req in user_requests)
        outstanding_balance = total_requested - total_paid
        
        if total_requested > 0:  # Only include users with requests
            user_spending.append({
                'user': user,
                'total_requests': user_requests.count(),
                'total_requested': total_requested,
                'total_paid': total_paid,
                'outstanding_balance': outstanding_balance,
                'pending_requests': user_requests.filter(status='Pending').count(),
                'approved_requests': user_requests.filter(status='Approved').count(),
                'paid_requests': user_requests.filter(status='Paid').count(),
                'payment_completion_rate': (total_paid / total_requested * 100) if total_requested > 0 else 0
            })
    
    # Sort by total requested (descending)
    user_spending.sort(key=lambda x: x['total_requested'], reverse=True)
    
    # Calculate totals
    totals = {
        'total_users': len(user_spending),
        'total_requested': sum(u['total_requested'] for u in user_spending),
        'total_paid': sum(u['total_paid'] for u in user_spending),
        'total_outstanding': sum(u['outstanding_balance'] for u in user_spending),
        'avg_request_value': sum(u['total_requested'] for u in user_spending) / len(user_spending) if user_spending else 0
    }
    
    context = {
        'user_spending': user_spending,
        'totals': totals,
        'filters': {
            'date_from': date_from,
            'date_to': date_to
        }
    }
    
    return render(request, 'reports/user_spending_report.html', context)


@login_required
def item_popularity_report(request):
    """Report showing most requested items"""
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    queryset = ConsumableRequestDetail.objects.select_related('item', 'request')
    
    # Apply date filters
    if date_from:
        queryset = queryset.filter(request__date_created__gte=date_from)
    if date_to:
        queryset = queryset.filter(request__date_created__lte=date_to)
    
    # Aggregate by item
    item_stats = queryset.values('item__title').annotate(
        total_quantity=Sum('quantity'),
        total_requests=Count('request', distinct=True),
        total_value=Sum('total_price'),
        avg_price=Avg('item_price')
    ).order_by('-total_quantity')
    
    context = {
        'item_stats': item_stats,
        'total_items': item_stats.count(),
        'filters': {
            'date_from': date_from,
            'date_to': date_to
        }
    }
    
    return render(request, 'reports/item_popularity_report.html', context)





@login_required
def payment_analysis_report(request):
    """Detailed payment analysis and trends with enhanced filtering and performance"""

    # Get filter parameters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    user_id = request.GET.get('user_id')
    status_filter = request.GET.get('status', 'all')

    # Validate and parse dates
    parsed_date_from = None
    parsed_date_to = None

    try:
        if date_from:
            parsed_date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        if date_to:
            parsed_date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

        if parsed_date_from and parsed_date_to and parsed_date_from > parsed_date_to:
            messages.error(request, "Start date cannot be after end date.")
            parsed_date_from = parsed_date_to = None

    except ValueError:
        messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
        parsed_date_from = parsed_date_to = None

    # Base queryset with optimized select_related
    queryset = PaybackConsumable.objects.select_related('consumable_request__user','consumable_request'
    ).prefetch_related('consumable_request__details__item')

    # Apply filters
    if parsed_date_from:
        queryset = queryset.filter(repayment_date__gte=parsed_date_from)
    if parsed_date_to:
        queryset = queryset.filter(repayment_date__lte=parsed_date_to)
    if user_id:
        queryset = queryset.filter(consumable_request__user_id=user_id)

    # Payment statistics
    payment_stats = queryset.aggregate(
        total_payments=Sum('amount_paid'),
        avg_payment=Avg('amount_paid'),
        payment_count=Count('id'),
        min_payment=Min('amount_paid'),
        max_payment=Max('amount_paid')
    )
    payment_stats = {k: v or 0 for k, v in payment_stats.items()}

    # Monthly trends
    monthly_payments = queryset.annotate(
        month=TruncMonth('repayment_date')
    ).values('month').annotate(
        total_paid=Sum('amount_paid'),
        payment_count=Count('id'),
        avg_payment=Avg('amount_paid')
    ).order_by('month')

    # Weekly trends for last 90 days
    three_months_ago = timezone.now().date() - timedelta(days=90)
    weekly_payments = queryset.filter(
        repayment_date__gte=three_months_ago
    ).annotate(
        week=TruncWeek('repayment_date')
    ).values('week').annotate(
        total_paid=Sum('amount_paid'),
        payment_count=Count('id')
    ).order_by('week')

    # Outstanding balances
    outstanding_filter = Q(status__in=['Pending', 'Approved', 'Partially Paid'])
    if status_filter != 'all':
        outstanding_filter &= Q(status=status_filter)

    outstanding_requests = ConsumableRequest.objects.filter(
        outstanding_filter
    ).select_related('user').prefetch_related(
        'details__item',           
        'repayments'    
    )

    outstanding_data = []
    total_outstanding = 0

    for req in outstanding_requests:
        total_price = req.calculate_total_price()
        total_paid = req.total_paid()
        balance = total_price - total_paid

        if balance > 0:
            days_outstanding = (timezone.now().date() - req.date_created.date()).days

            # Urgency levels
            if days_outstanding > 90:
                urgency = 'critical'
            elif days_outstanding > 60:
                urgency = 'high'
            elif days_outstanding > 30:
                urgency = 'medium'
            else:
                urgency = 'low'

            outstanding_data.append({
                'request': req,
                'total_price': total_price,
                'total_paid': total_paid,
                'balance': balance,
                'days_outstanding': days_outstanding,
                'urgency': urgency,
                'payment_percentage': (total_paid / total_price * 100) if total_price > 0 else 0
            })

            total_outstanding += balance

    # Sort by highest balance then by days outstanding
    outstanding_data.sort(key=lambda x: (x['balance'], x['days_outstanding']), reverse=True)

    # Payment method analysis (if field exists)
    payment_methods = queryset.values('payment_method').annotate(
        total_paid=Sum('amount_paid'),
        count=Count('id')
    ).order_by('-total_paid') if hasattr(PaybackConsumable, 'payment_method') else []

    # Top 10 users
    top_users = queryset.values(
        'consumable_request__user__username',
        'consumable_request__user__first_name',
        'consumable_request__user__last_name'
    ).annotate(
        total_paid=Sum('amount_paid'),
        payment_count=Count('id')
    ).order_by('-total_paid')[:10]

    # Outstanding summary by urgency
    outstanding_summary = {
        'critical': len([x for x in outstanding_data if x['urgency'] == 'critical']),
        'high': len([x for x in outstanding_data if x['urgency'] == 'high']),
        'medium': len([x for x in outstanding_data if x['urgency'] == 'medium']),
        'low': len([x for x in outstanding_data if x['urgency'] == 'low']),
    }

    # Recent payments (last 30 days)
    recent_payments = queryset.filter(
        repayment_date__gte=timezone.now().date() - timedelta(days=30)
    ).select_related('consumable_request__user').order_by('-repayment_date')[:10]

    # Month filter options
    month_list = ConsumableRequest.objects.dates('date_created', 'month', order='DESC')

    # User filter dropdown
    users_list = ConsumableRequest.objects.select_related('user').values(
        'user__id', 'user__username', 'user__first_name', 'user__last_name'
    ).distinct().order_by('user__username')

    context = {
        'payment_stats': payment_stats,'monthly_payments': list(monthly_payments),
        'weekly_payments': list(weekly_payments),'outstanding_data': outstanding_data,
        'outstanding_summary': outstanding_summary,'payment_methods': payment_methods,
        'top_users': top_users,'recent_payments': recent_payments,
        'months': month_list,'users_list': users_list,'total_outstanding': total_outstanding,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'user_id': user_id,
            'status': status_filter
        },
        'date_range_summary': {
            'start': parsed_date_from,
            'end': parsed_date_to,
            'days': (parsed_date_to - parsed_date_from).days if parsed_date_from and parsed_date_to else None
        }
    }

    return render(request, 'reports/consumable_payment_analysis_report.html', context)


@login_required
def approval_workflow_report(request):
    """Report on approval workflow and approver statistics"""
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    queryset = ConsumableRequest.objects.select_related('user', 'approved_by')
    
    # Apply date filters
    if date_from:
        queryset = queryset.filter(date_created__gte=date_from)
    if date_to:
        queryset = queryset.filter(date_created__lte=date_to)
    
    # Approval statistics
    approval_stats = {
        'total_requests': queryset.count(),
        'pending_requests': queryset.filter(status='Pending').count(),
        'approved_requests': queryset.filter(status='Approved').count(),
        'declined_requests': queryset.filter(status='Declined').count(),
        'paid_requests': queryset.filter(status='Paid').count(),
    }
    
    # Calculate approval rates
    total_processed = approval_stats['approved_requests'] + approval_stats['declined_requests'] + approval_stats['paid_requests']
    approval_stats['approval_rate'] = (
        (approval_stats['approved_requests'] + approval_stats['paid_requests']) / total_processed * 100
    ) if total_processed > 0 else 0
    
    # Approver statistics
    

# Build approver stats in Python
    approver_dict = defaultdict(lambda: {'total_approved': 0, 'total_value_approved': 0})

    for req in queryset.filter(approved_by__isnull=False):
        username = req.approved_by.username
        approver_dict[username]['total_approved'] += 1
        approver_dict[username]['total_value_approved'] += req.calculate_total_price()

    # Convert to list and sort
    approver_stats = [
        {'approved_by__username': username, **stats}
        for username, stats in approver_dict.items()
    ]
    approver_stats.sort(key=lambda x: x['total_approved'], reverse=True)

    
    # Average approval time (for approved requests with approval_date)
    approved_requests = ConsumableRequestDetail.objects.filter(
        approval_date__isnull=False
    ).select_related('request')
    
    approval_times = []
    for detail in approved_requests:
        days_to_approve = (detail.approval_date - detail.request.date_created.date()).days
        approval_times.append(days_to_approve)
    
    avg_approval_time = sum(approval_times) / len(approval_times) if approval_times else 0
    
    context = { 'approval_stats': approval_stats, 'approver_stats': approver_stats,'avg_approval_time': avg_approval_time,
        'filters': {
            'date_from': date_from,
            'date_to': date_to
        }
    }
    
    return render(request, 'reports/consumable_approval_workflow_report.html', context)


@login_required
def export_report_csv(request):
    """Export reports to CSV format"""
    
    report_type = request.GET.get('type', 'requests')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
    
    writer = csv.writer(response)
    
    if report_type == 'requests':
        # Export all requests
        writer.writerow(['ID', 'User', 'Date Created', 'Status', 'Approved By', 'Total Price', 'Total Paid', 'Balance'])
        
        for req in ConsumableRequest.objects.select_related('user', 'approved_by'):
            writer.writerow([
                req.id,
                req.user.username,
                req.date_created.strftime('%Y-%m-%d'),
                req.status,
                req.approved_by.username if req.approved_by else '',
                req.calculate_total_price(),
                req.total_paid(),
                req.balance()
            ])
    
    elif report_type == 'payments':
        # Export all payments
        writer.writerow(['Request ID', 'User', 'Amount Paid', 'Payment Date', 'Balance Remaining'])
        
        for payment in PaybackConsumable.objects.select_related('consumable_request__user'):
            writer.writerow([
                payment.consumable_request.id,
                payment.consumable_request.user.username,
                payment.amount_paid,
                payment.repayment_date.strftime('%Y-%m-%d'),
                payment.balance_remaining or 0
            ])
    
    elif report_type == 'user_spending':
        # Export user spending summary
        writer.writerow(['User', 'Total Requests', 'Total Requested', 'Total Paid', 'Outstanding Balance', 'Completion Rate'])
        
        for user in User.objects.all():
            user_requests = ConsumableRequest.objects.filter(user=user)
            total_requested = sum(req.calculate_total_price() for req in user_requests)
            total_paid = sum(req.total_paid() for req in user_requests)
            
            if total_requested > 0:
                completion_rate = (total_paid / total_requested * 100) if total_requested > 0 else 0
                writer.writerow([
                    user.username,
                    user_requests.count(),
                    total_requested,
                    total_paid,
                    total_requested - total_paid,
                    f"{completion_rate:.1f}%"
                ])
    
    return response


@login_required
def report_api_data(request):
    """API endpoint for chart data"""
    
    chart_type = request.GET.get('chart', 'monthly_trends')
    
    if chart_type == 'monthly_trends':
        # Monthly request and payment trends
        end_date = timezone.now()
        start_date = end_date - timedelta(days=365)
        
        monthly_data = ConsumableRequest.objects.filter(
            date_created__range=[start_date, end_date]
        ).annotate(
            month=TruncMonth('date_created')
        ).values('month').annotate(
            request_count=Count('id'),
            total_value=Sum('details__total_price')
        ).order_by('month')
        
        return JsonResponse({
            'labels': [item['month'].strftime('%Y-%m') for item in monthly_data],
            'request_counts': [item['request_count'] for item in monthly_data],
            'total_values': [float(item['total_value'] or 0) for item in monthly_data]
        })
    
    elif chart_type == 'status_distribution':
        # Request status distribution
        status_data = ConsumableRequest.objects.values('status').annotate(
            count=Count('id')
        )
        
        return JsonResponse({
            'labels': [item['status'] for item in status_data],
            'data': [item['count'] for item in status_data]
        })
    
    elif chart_type == 'top_items':
        # Top 10 most requested items
        top_items = ConsumableRequestDetail.objects.values('item__title').annotate(
            total_quantity=Sum('quantity')
        ).order_by('-total_quantity')[:10]
        
        return JsonResponse({
            'labels': [item['item__title'] for item in top_items],
            'data': [item['total_quantity'] for item in top_items]
        })
    
    return JsonResponse({'error': 'Invalid chart type'}, status=400)