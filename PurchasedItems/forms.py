from django import forms
from django.core.validators import MinValueValidator
from decimal import Decimal
from.models import *

class ConsumablePurchasedRequestForm(forms.ModelForm):
    class Meta:
        model = ConsumablePurchasedRequest
        fields = ['item','purpose', 'amount_requested', 'remarks']
        widgets = {
            'item': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Rice.',
                'maxlength': 255
            }),
            'purpose': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Office supplies, Cleaning materials, etc.',
                'maxlength': 255
            }),
            'amount_requested': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Additional details or justification for this request...',
                'rows': 4,
                'maxlength': 500
            })
        }
        labels = {
            'Item': 'Item',
            'purpose': 'Purpose',
            'amount_requested': 'Amount Requested (₦)',
            'remarks': 'Remarks (Optional)'
        }
        help_texts = {
            'purpose': 'Briefly describe what you need to purchase',
            'amount_requested': 'Enter the estimated amount in Nigerian Naira',
            'remarks': 'Any additional information or justification'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make amount_requested required and add validation
        self.fields['amount_requested'].validators.append(
            MinValueValidator(Decimal('0.01'), message="Amount must be greater than zero")
        )
        
        # Add custom validation messages
        self.fields['purpose'].error_messages = {
            'required': 'Please specify the purpose of this request',
            'max_length': 'Purpose cannot exceed 255 characters'
        }
        
        self.fields['amount_requested'].error_messages = {
            'required': 'Please enter the requested amount',
            'invalid': 'Please enter a valid amount'
        }
        self.fields['item'].error_messages = {
            'required': 'Please enter the requested amount',
            'invalid': 'Please enter a valid amount'
        }

    def clean_item(self):
        purpose = self.cleaned_data.get('item')
        if item:
            # Remove extra whitespace and ensure it's not just spaces
            item = item.strip()
            if not item:
                raise forms.ValidationError("item cannot be empty or just spaces")
            
            # Check for minimum length
            if len(item) < 3:
                raise forms.ValidationError("item must be at least 3 characters long")
        
        return item
    
    def clean_purpose(self):
        purpose = self.cleaned_data.get('purpose')
        if purpose:
            # Remove extra whitespace and ensure it's not just spaces
            purpose = purpose.strip()
            if not purpose:
                raise forms.ValidationError("Purpose cannot be empty or just spaces")
            
            # Check for minimum length
            if len(purpose) < 3:
                raise forms.ValidationError("Purpose must be at least 3 characters long")
        
        return purpose

    def clean_amount_requested(self):
        amount = self.cleaned_data.get('amount_requested')
        if amount:
            # Check for reasonable maximum (adjust as needed)
            if amount > 10000000:  # 10 million naira
                raise forms.ValidationError("Amount cannot exceed ₦10,000,000")
            
            # Round to 2 decimal places
            amount = round(amount, 2)
        
        return amount

    def clean_remarks(self):
        remarks = self.cleaned_data.get('remarks')
        if remarks:
            remarks = remarks.strip()
            # If remarks is just whitespace, make it empty
            if not remarks:
                remarks = ''
        return remarks

    def clean(self):
        cleaned_data = super().clean()
        purpose = cleaned_data.get('purpose')
        amount = cleaned_data.get('amount_requested')
        
        # Additional cross-field validation if needed
        if purpose and amount:
            # Example: Check if high amounts have detailed purpose
            if amount > 100000 and len(purpose) < 10:
                raise forms.ValidationError(
                    "For amounts above ₦100,000, please provide a more detailed purpose"
                )
        
        return cleaned_data

class PurchasedItemForm(forms.ModelForm):
    class Meta:
        model = PurchasedItem
        fields = ['item_name', 'quantity', 'unit_price', 'receipt','expenditure_amount']
        widgets = {
            'item_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter item name'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'expenditure_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'receipt': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png,.pdf'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields required
        self.fields['item_name'].required = True
        self.fields['quantity'].required = True
        self.fields['unit_price'].required = True
        self.fields['expenditure_amount'].required = True
        self.fields['receipt'].required = False




class SellingPlanForm(forms.ModelForm):
    class Meta:
        model = SellingPlan
        fields = [ 'selling_price_per_unit', 'quantity', 'notes']        



class ProfitCalculatorForm(forms.Form):
    selling_price = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Enter selling price'
        })
    )
    quantity_to_sell = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter quantity to sell'
        })
    )        