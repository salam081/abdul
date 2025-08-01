
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum,  FloatField, ExpressionWrapper
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.forms import modelformset_factory
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from .models import ConsumablePurchasedRequest, PurchasedItem
from accounts.decorator import group_required
from .forms import *
from  .forms import ProfitCalculatorForm
from .models import *
from accounts.models import *
from consumable.models import *
from main.models import *
from memberapp.models import *
from .models import *


@login_required
def purchase_consumable_dashboard(request):
    if  request.user.is_staff:
        requests = ConsumablePurchasedRequest.objects.all()
    else:
        requests = ConsumablePurchasedRequest.objects.filter(requested_by=request.user)

    # Stats
    total_requests = requests.count()
    pending_requests = requests.filter(status='pending').count()
    approved_requests = requests.filter(status='approved').count()
    accounted_requests = requests.filter(status='accounted').count()

    # Total approved amount
    total_requested = requests.aggregate(
        total=Sum('approved_amount')
    )['total'] or 0

    # Total spent (items + expenditure)
    total_spent = PurchasedItem.objects.filter(
        consumable_purchased_request__in=requests
    ).aggregate(
        total=Sum(
            ExpressionWrapper(
                F('quantity') * F('unit_price') + F('expenditure_amount'),
                output_field=DecimalField()
            )
        )
    )['total'] or 0

    # Remaining balance
    balance_remaining = total_requested - total_spent

    # Recent requests
    recent_requests = requests.order_by('-date_requested')[:10]

    context = {
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'accounted_requests': accounted_requests,
        'total_requested': total_requested,
        'total_spent': total_spent,
        'balance_remaining': balance_remaining,
        'recent_requests': recent_requests,
    }

    return render(request, 'consumables/purchase_consumable_dashboard.html', context)

# API Views for AJAX calls
@login_required
@require_http_methods(["GET"])
def purchase_request_balance_api(request, pk):
    """API endpoint to get request balance information"""
    consumable_request = get_object_or_404(ConsumablePurchasedRequest, pk=pk)
    # Check permissions
    if (
    not (request.user.group and request.user.group.title == 'admin')
    and consumable_request.requested_by != request.use):
        messages.error(request, "You don’t have permission to perform this action.")
    # if not request.user.is_staff and consumable_request.requested_by != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    data = {
        'amount_requested': float(consumable_request.amount_requested),
        'total_spent': float(consumable_request.total_spent()),
        'balance_remaining': float(consumable_request.balance_remaining()),
        'is_fully_accounted': consumable_request.is_fully_accounted(),}
    return JsonResponse(data)

@login_required
def consumable_purchase_request_create(request):
    """Create a new consumable request"""
    if request.method == 'POST':
        item = request.POST.get('item')
        purpose = request.POST.get('purpose')
        amount_requested = request.POST.get('amount_requested')
        remarks = request.POST.get('remarks')

        new_request = ConsumablePurchasedRequest.objects.create(
            item=item,purpose=purpose,
            requested_by = request.user,
            amount_requested=amount_requested,
            approved_amount=0,
            remarks=remarks) 
        new_request.save()   

        messages.success(request, 'Item request created successfully!')
        return redirect('consumable_purchase_request_detail', pk=new_request.pk)
    return render(request, 'consumables/purchase_request_form.html',)


@login_required
def purchase_request_list(request):
    """List all consumable requests with filtering and pagination"""
    requests = ConsumablePurchasedRequest.objects.all().order_by('-date_requested')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    # Filter by user (for non-staff users, show only their requests)
    if not request.user.is_staff :
        requests = requests.filter(requested_by=request.user)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        requests = requests.filter(
            Q(purpose__icontains=search_query) |
            Q(requested_by__username__icontains=search_query) |
            Q(remarks__icontains=search_query)
        )
    # Pagination
    paginator = Paginator(requests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'page_obj': page_obj,
        'status_choices': ConsumablePurchasedRequest.STATUS_CHOICES,
        'current_status': status_filter,'search_query': search_query,}
    return render(request, 'consumables/purchase_request_list.html', context)

@login_required
def consumable_purchase_request_detail(request, pk):
    """View details of a specific consumable request"""
    consumable_request = get_object_or_404(ConsumablePurchasedRequest, pk=pk)
    
    # Check permissions
    if (not (request.user.group and request.user.group.title == 'admin')
         and consumable_request.requested_by != request.user):
   
    # if not request.user.is_staff and consumable_request.requested_by != request.user:
        messages.error(request, "You don't have permission to view this request.")
        return redirect('consumable_request_list')
    
    purchased_items = consumable_request.items.all()
    
    context = {
        'consumable_request': consumable_request,
        'purchased_items': purchased_items,
        'total_spent': consumable_request.total_spent(),
        'balance_remaining': consumable_request.balance_remaining(),}
    return render(request, 'consumables/purchase_request_detail.html', context)


@login_required
def purchase_consumable_request_update(request, pk):
    """Update a consumable request"""
    consumable_request = get_object_or_404(ConsumablePurchasedRequest, pk=pk)

    if (
        not (request.user.group and request.user.group.title == 'admin')
        and consumable_request.requested_by != request.user
    ):
        messages.error(request, "You don't have permission to edit this request.")
        return redirect('consumable_purchase_request_detail', pk=pk)

    if consumable_request.status != 'pending':
        messages.error(request, "Cannot edit request that has been approved or accounted.")
        return redirect('consumable_purchase_request_detail', pk=pk)

    if request.method == 'POST':
        item = request.POST.get('item')
        purpose = request.POST.get('purpose')
        amount_requested = request.POST.get('amount_requested')
        remarks = request.POST.get('remarks')

        consumable_request.item = item
        consumable_request.purpose = purpose
        consumable_request.amount_requested = amount_requested or 0
        consumable_request.remarks = remarks
        consumable_request.approved_amount = 0  # reset approval
        consumable_request.requested_by = request.user  # keep the requesting user
        consumable_request.save()

        messages.success(request, "Consumable request updated successfully.")
        return redirect('consumable_purchase_request_detail', pk=pk)

    context = {
        'title': 'Update Consumable Request',
        'consumable_request': consumable_request,
    }
    return render(request, 'consumables/purchase_update_form.html', context)

@login_required
def consumable_purchase_request_delete(request, pk):
    """Delete a consumable request"""
    consumable_request = get_object_or_404(ConsumablePurchasedRequest, pk=pk)
    
    # Check permissions
    if (not (request.user.group and request.user.group.title == 'admin')
    and consumable_request.requested_by != request.user):
   
        messages.error(request, "You don't have permission to delete this request.")
        return redirect('consumable_purchase_request_detail', pk=pk)
    
    # Only allow deletion if request is pending
    if consumable_request.status != 'pending':
        messages.error(request, "Cannot delete request that has been approved or accounted.")
        return redirect('consumable_purchase_request_detail', pk=pk)
    
    if request.method == 'POST':
        consumable_request.delete()
        messages.success(request, 'Consumable request deleted successfully!')
        return redirect('purchase_request_list')
    
    return render(request, 'consumables/purchase_request_confirm_delete.html', {
        'consumable_request': consumable_request
    })

@login_required
def consumable_purchase_request_approve(request, pk):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to approve requests.")
        return redirect('consumable_purchase_request_detail', pk=pk)

    consumable_request = get_object_or_404(ConsumablePurchasedRequest, pk=pk)

    if consumable_request.status != 'pending':
        messages.error(request, "Request has already been processed.")
        return redirect('consumable_purchase_request_detail', pk=pk)
    
    if request.method == 'POST':
        approved_amount = request.POST.get('approved_amount')

        try:
            approved_amount = float(approved_amount)
        except (TypeError, ValueError):
            messages.error(request, 'Invalid approved amount.')
            return redirect('consumable_purchase_request_approve', pk=pk)
        consumable_request.status = 'approved'
        consumable_request.approved_amount = approved_amount
        consumable_request.approved_by = request.user
        consumable_request.date_approved = timezone.now().date()
        consumable_request.save()

        messages.success(request, 'Request approved successfully!')
        return redirect('consumable_purchase_request_detail', pk=pk)
    context =  {'consumable_request': consumable_request}
    return render(request, 'consumables/purchase_request_approve.html',context)

@login_required
def purchased_item_create(request, request_pk):
    consumable_request = get_object_or_404(ConsumablePurchasedRequest, pk=request_pk)

    # Access checks...
    if (not (request.user.group and request.user.group.title == 'admin')
          and consumable_request.requested_by != request.user):
   
        messages.error(request, "You don't have permission to add items to this request.")
        return redirect('consumable_purchase_request_detail', pk=request_pk)

    if consumable_request.status != 'approved':
        messages.error(request, "Only approved requests can have purchased items.")
        return redirect('consumable_purchase_request_detail', pk=request_pk)

    # ✅ Total spent = quantity * unit_price + expenditure_amount
    total_spent = consumable_request.items.aggregate(
        total=Sum(
            ExpressionWrapper(
                F('quantity') * F('unit_price') + F('expenditure_amount'),
                output_field=DecimalField()
            )
        )
    )['total'] or 0

    approved_amount = consumable_request.approved_amount or 0
    balance_remaining = approved_amount - total_spent

    if balance_remaining <= 0:
        messages.warning(request, f"₦{approved_amount:.2f} already spent. No balance remaining.")
        return redirect('consumable_purchase_request_detail', pk=request_pk)

    if request.method == 'POST':
        form = PurchasedItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.consumable_purchased_request = consumable_request
            item.requested_by = request.user
            item.date_added = timezone.now()
            # ✅ Calculate full total of this new item
            new_item_total = (item.quantity * item.unit_price) + item.expenditure_amount

            if new_item_total > balance_remaining:
                messages.error(
                    request,
                    f"This item (₦{new_item_total:.2f}) exceeds the remaining balance or Approved Amount  (₦{balance_remaining:.2f})."
                )
                return redirect('consumable_purchase_request_detail', pk=request_pk)
            item.save()
            messages.success(request, 'Purchased item added successfully!')
            return redirect('consumable_purchase_request_detail', pk=request_pk)
    else:
        form = PurchasedItemForm()
    context = {'form': form,'consumable_request': consumable_request,
        'title': 'Add Purchased Item','balance_remaining': balance_remaining, }
    return render(request, 'consumables/item_form.html', context )

@login_required
def consumable_request_mark_accounted(request, pk):
    """Mark a consumable request as fully accounted"""
    consumable_request = get_object_or_404(ConsumablePurchasedRequest, pk=pk)
    # Check permissions
    if (not (request.user.group and request.user.group.title == 'admin')
        and consumable_request.requested_by != request.user):
        messages.error(request, "You don't have permission to modify this request.")
        return redirect('consumable_purchase_request_detail', pk=pk)
    
    if consumable_request.status != 'approved':
        messages.error(request, "Request must be approved before marking as accounted.")
        return redirect('consumable_purchase_request_detail', pk=pk)
    
    if request.method == 'POST':
        consumable_request.status = 'accounted'
        consumable_request.requested_by = request.user
        consumable_request.date_requested = timezone.now()
        consumable_request.save()
        messages.success(request, 'Consumable request marked as fully accounted!')
        return redirect('consumable_purchase_request_detail', pk=pk)
    
    return render(request, 'consumables/purchase_request_mark_accounted.html', {'consumable_request': consumable_request})

@login_required
def selling_plan_list(request):
    """Display list of all selling plans with search and filtering"""
    selling_plans = SellingPlan.objects.select_related('purchased_item', 'created_by').all()
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        selling_plans = selling_plans.filter(
            Q(purchased_item__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Date range filtering
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        selling_plans = selling_plans.filter(date_created__gte=date_from)
    if date_to:
        selling_plans = selling_plans.filter(date_created__lte=date_to)
    
    # Annotate with line total
    selling_plans = selling_plans.annotate(
        line_total=ExpressionWrapper(
            F('selling_price_per_unit') * F('quantity'),
            output_field=FloatField()
        )
    )
    
    # Calculate total sale value
    total_value = selling_plans.aggregate(total=Sum('line_total'))['total'] or 0
    # Pagination
    paginator = Paginator(selling_plans, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'date_from': date_from,'date_to': date_to,
        'total_value': total_value,}
    return render(request, 'consumables/selling_plan_list.html', context)


@login_required
def selling_plan_create(request, pk):
    consumable_request = get_object_or_404(PurchasedItem, pk=pk)
    
    if ( not (request.user.group and request.user.group.title == 'admin' or request.user.group.title == 'staff')
            and consumable_request.requested_by != request.user):
   
        messages.error(request, "You don't have permission to create this selling plan.")
        return redirect('selling_plan_detail', pk=pk)
    
    existing_plan = SellingPlan.objects.filter(purchased_item=consumable_request).first()
    if existing_plan:
        messages.warning(request, "A selling plan already exists for this item.")
        return redirect('selling_plan_detail', pk=existing_plan.pk)
   
    profit = None
    total_sale_amount = None
    total_purchase_cost = None

    if request.method == 'POST':
        form = SellingPlanForm(request.POST)
        if form.is_valid():
            unit_price = form.cleaned_data['selling_price_per_unit']
            quantity = form.cleaned_data['quantity']

            total_sale_amount = unit_price * quantity
            total_purchase_cost = (consumable_request.unit_price * quantity) + consumable_request.expenditure_amount
            profit = total_sale_amount - total_purchase_cost

            selling_plan = form.save(commit=False)
            selling_plan.purchased_item = consumable_request
            selling_plan.selling_price_per_unit = unit_price
            selling_plan.quantity = quantity
            selling_plan.profit = profit
            selling_plan.created_by = request.user
            selling_plan.date_created = timezone.now()
            selling_plan.save()

            messages.success(request, f'Profit calculated and saved: ₦{profit}')
            # return redirect('selling_plan_detail', pk=pk)
    else:
        form = SellingPlanForm()

    context = {
        'consumable_request': consumable_request,
        'purchased_items': consumable_request,
        'purchased_item': consumable_request,
        'form': form,'profit': profit,
        'total_sale_amount': total_sale_amount,
        'total_purchase_cost': total_purchase_cost,}

    return render(request, 'consumables/selling_plan_create.html', context)

@login_required
def selling_plan_detail(request, pk):
    selling_plan = get_object_or_404(SellingPlan, pk=pk)
    purchased_item = selling_plan.purchased_item
    # Calculate total purchase cost: (unit_price * selling_quantity) + expenditure_amount
    total_purchase_cost = (purchased_item.unit_price * selling_plan.quantity) + purchased_item.expenditure_amount
    # Calculate potential profit
    potential_profit = selling_plan.total_sale_value - total_purchase_cost
    context = {'selling_plan': selling_plan,'potential_profit': potential_profit,'total_purchase_cost': total_purchase_cost,}
    return render(request, 'consumables/selling_plan_detail.html', context)


@login_required
def selling_plan_update(request, pk):
    """Edit an existing selling plan"""
    selling_plan = get_object_or_404(SellingPlan, pk=pk)
    purchased_item = selling_plan.purchased_item
    consumable_request = purchased_item.consumable_purchased_request

    # Permissions: only admin or request owner can edit
    if (not (request.user.group and request.user.group.title == 'admin' or request.user.group.title == 'staff') and
        consumable_request.requested_by != request.user):
        messages.error(request, "You don't have permission to edit this selling plan.")
        return redirect('selling_plan_detail', pk=pk)

    profit = None
    total_sale_amount = None
    total_purchase_cost = None

    if request.method == 'POST':
        form = SellingPlanForm(request.POST, instance=selling_plan)
        if form.is_valid():
            unit_price = form.cleaned_data['selling_price_per_unit']
            quantity = form.cleaned_data['quantity']

            total_sale_amount = unit_price * quantity
            total_purchase_cost = (purchased_item.unit_price * quantity) + purchased_item.expenditure_amount
            profit = total_sale_amount - total_purchase_cost

            updated_plan = form.save(commit=False)
            updated_plan.profit = profit
            updated_plan.save()

            messages.success(request, f'Selling plan updated. New profit: ₦{profit}')
            return redirect('selling_plan_detail', pk=selling_plan.pk)
    else:
        form = SellingPlanForm(instance=selling_plan)

    context = { 'form': form,'selling_plan': selling_plan,'purchased_item': purchased_item,
        'consumable_request': consumable_request,'profit': profit,'total_sale_amount': total_sale_amount,
        'total_purchase_cost': total_purchase_cost,'title': 'Update Selling Plan',}
    return render(request, 'consumables/selling_plan_create.html', context)


@login_required
def selling_plan_delete(request, pk):
    """Delete a selling plan"""
    selling_plan = get_object_or_404(SellingPlan, pk=pk)
    purchased_item = selling_plan.purchased_item
    consumable_request = purchased_item.consumable_purchased_request

    # Permission check: only admin or request owner can delete
    if (not (request.user.group and request.user.group.title == 'admin' or request.user.group.title == 'staff') and consumable_request.requested_by != request.user):
        messages.error(request, "You don't have permission to delete this selling plan.")
        return redirect('selling_plan_detail', pk=selling_plan.pk)

    selling_plan.delete()
    messages.success(request, "Selling plan deleted successfully.")
    return redirect('consumable_purchase_request_detail', pk=consumable_request.pk)


