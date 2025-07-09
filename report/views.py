

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Avg
from django.db.models.functions import TruncMonth, TruncYear
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal
from django.db.models import F, Sum, ExpressionWrapper, DecimalField
import json
from consumable.models import ConsumableRequest, ConsumableRequestDetail, PaybackConsumable
from accounts.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
import csv

# Create your views here.

from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from django.db.models import F, Sum, Count, ExpressionWrapper, DecimalField

# class ReportingDashboardView(LoginRequiredMixin, TemplateView):
#     template_name = 'reports/consumable_dashboard.html'

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)

#         context['total_requests'] = ConsumableRequest.objects.count()
#         context['pending_requests'] = ConsumableRequest.objects.filter(status='Pending').count()
#         context['approved_requests'] = ConsumableRequest.objects.filter(status='Approved').count()
#         context['paid_requests'] = ConsumableRequest.objects.filter(status='Paid').count()

#         # Financial totals using annotation
#         total_value = ConsumableRequestDetail.objects.annotate(
#             total_price=ExpressionWrapper(F('item_price') * F('quantity'), output_field=DecimalField())
#         ).aggregate(total=Sum('total_price'))['total'] or 0

#         total_paid = PaybackConsumable.objects.aggregate(total=Sum('amount_paid'))['total'] or 0

#         context['total_request_value'] = total_value
#         context['total_paid_amount'] = total_paid
#         context['outstanding_balance'] = total_value - total_paid

#         context['monthly_data'] = self.get_monthly_trends()

#         return context

#     def get_monthly_trends(self):
#         end_date = timezone.now()
#         start_date = end_date - timedelta(days=365)

#         # Monthly requests
#         monthly_requests = ConsumableRequest.objects.filter(
#             date_created__range=[start_date, end_date]
#         ).annotate(
#             month=TruncMonth('date_created')
#         ).values('month').annotate(
#             count=Count('id')
#         ).order_by('month')

#         # Monthly payments
#         monthly_payments = PaybackConsumable.objects.filter(
#             repayment_date__range=[start_date, end_date]
#         ).annotate(
#             month=TruncMonth('repayment_date')
#         ).values('month').annotate(
#             total_paid=Sum('amount_paid')
#         ).order_by('month')

#         return {
#             'requests': list(monthly_requests),
#             'payments': list(monthly_payments)
#         }

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
import json
from django.utils.safestring import mark_safe
import json
from django.utils.safestring import mark_safe


from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import timedelta, date, datetime
from decimal import Decimal
import json

# from .models import ConsumableRequest, ConsumableRequestDetail, PaybackConsumable





@login_required
def request_status_report(request):
    """Detailed report of all requests grouped by status"""
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    user_filter = request.GET.get('user')
    
    # Base queryset
    queryset = ConsumableRequest.objects.select_related('user', 'approved_by')
    
    # Apply filters
    if status_filter != 'all':
        queryset = queryset.filter(status=status_filter)
    
    if date_from:
        queryset = queryset.filter(date_created__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(date_created__lte=date_to)
    
    if user_filter:
        queryset = queryset.filter(user_id=user_filter)
    
    # Add calculated fields
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
            'items_count': req.details.count()
        })
    
    # Pagination
    paginator = Paginator(requests_data, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Summary statistics
    summary = {
        'total_requests': queryset.count(),
        'total_value': sum(req.calculate_total_price() for req in queryset),
        'total_paid': sum(req.total_paid() for req in queryset),
        'pending_count': queryset.filter(status='Pending').count(),
        'approved_count': queryset.filter(status='Approved').count(),
        'paid_count': queryset.filter(status='Paid').count(),
        'declined_count': queryset.filter(status='Declined').count(),
    }
    
    context = {
        'requests': page_obj,
        'summary': summary,
        'users': User.objects.all(),
        'filters': {
            'status': status_filter,
            'date_from': date_from,
            'date_to': date_to,
            'user': user_filter
        }
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
    """Detailed payment analysis and trends"""
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    queryset = PaybackConsumable.objects.select_related('consumable_request__user')
    
    # Apply date filters
    if date_from:
        queryset = queryset.filter(repayment_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(repayment_date__lte=date_to)
    
    # Payment statistics
    payment_stats = queryset.aggregate(
        total_payments=Sum('amount_paid'),
        avg_payment=Avg('amount_paid'),
        payment_count=Count('id')
    )
    
    # Monthly payment trends
    monthly_payments = queryset.annotate(
        month=TruncMonth('repayment_date')
    ).values('month').annotate(
        total_paid=Sum('amount_paid'),
        payment_count=Count('id')
    ).order_by('month')
    
    # Outstanding balances
    outstanding_requests = ConsumableRequest.objects.exclude(status='Paid').select_related('user')

    outstanding_data = []
    for req in outstanding_requests:
        total_price = req.calculate_total_price()
        total_paid = req.total_paid()
        balance = total_price - total_paid

        if balance > 0:
            outstanding_data.append({
                'request': req,
                'total_price': total_price,
                'total_paid': total_paid,
                'balance': balance,
                'days_outstanding': (timezone.now().date() - req.date_created.date()).days
            })

        # Sort by balance (highest first)
        outstanding_data.sort(key=lambda x: x['balance'], reverse=True)
        
    context = {
        'payment_stats': payment_stats,
        'monthly_payments': monthly_payments,
        'outstanding_data': outstanding_data,
        'total_outstanding': sum(item['balance'] for item in outstanding_data),
        'filters': {
            'date_from': date_from,
            'date_to': date_to
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
    
    context = {
        'approval_stats': approval_stats,
        'approver_stats': approver_stats,
        'avg_approval_time': avg_approval_time,
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