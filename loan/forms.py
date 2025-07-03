from django  import forms

from .models import *




class LoanSettingsForm(forms.ModelForm):
    class Meta:
        model = LoanSettings
        fields = ['allow_loan_requests', 'allow_consumable_requests']        