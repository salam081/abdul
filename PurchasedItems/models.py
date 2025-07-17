from django.db import models
from accounts.models import *
from consumable.models import *
from main.models import *
from memberapp.models import *

# Create your models here.


class ConsumablePurchasedRequest(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'),('approved', 'Approved'),('accounted', 'Fully Accounted'),]
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)#,related_name='requested_by_purchest'
    item = models.CharField(max_length=255)
    purpose = models.CharField(max_length=255)
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='consumable_approvals')
    date_requested = models.DateField(auto_now_add=True)
    date_approved = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    def total_spent(self):
        return sum(item.total_price for item in self.items.all())

    def balance_remaining(self):
        return self.approved_amount - self.total_spent()

    def is_fully_accounted(self):
        return self.status == 'accounted'

    def __str__(self):
        return f"{self.requested_by} | ₦{self.amount_requested} | {self.status}"


class PurchasedItem(models.Model):
    consumable_purchased_request = models.ForeignKey(ConsumablePurchasedRequest, on_delete=models.CASCADE, related_name='items'  )
    item_name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)
    expenditure_amount  = models.DecimalField(max_digits=10, decimal_places=2)
    date_added = models.DateField(auto_now_add=True)
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price + self.expenditure_amount
    
    def __str__(self):
        return f"{self.item_name}  | ₦{self.unit_price} | ₦{self.consumable_purchased_request} | {self.quantity}"


class SellingPlan(models.Model):
    purchased_item = models.OneToOneField(PurchasedItem, on_delete=models.CASCADE, related_name='selling_plan')
    selling_price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_created = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    profit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)


    @property
    def total_sale_value(self):
        return self.selling_price_per_unit * self.quantity 
    

    def __str__(self):
        return f"{self.purchased_item} | ₦{self.selling_price_per_unit} | {self.quantity}"

