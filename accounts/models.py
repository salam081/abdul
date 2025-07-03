from django.db import models
from django.contrib.auth.models import AbstractUser
from django_countries.fields import CountryField
from main.models import Savings
from decimal import Decimal
from main.models import *
# Create your models here.

class UserGroup(models.Model):
    title = models.CharField(max_length=50)

    def __str__(self):
        return self.title
    
class Gender(models.Model):
    title = models.CharField(max_length=50)

    def __str__(self):
        return self.title
    
class MaritalStatus(models.Model):
    title = models.CharField(max_length=20)

    def __str__(self):
        return self.title

class Religion(models.Model):
    title = models.CharField(max_length=20)

    def __str__(self):
        return self.title

    
class User(AbstractUser):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    other_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(blank=True,null=True)
    username = models.CharField(max_length=100, unique=True)
    savings = models.IntegerField(blank=True,null=True)
    account_type = models.CharField(max_length=100,blank=True,null=True)
    department = models.CharField(max_length=100)
    unit = models.CharField(max_length=100)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE, blank=True, null=True)
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, blank=True, null=True)
    marital_status = models.ForeignKey(MaritalStatus,on_delete=models.SET_NULL, null=True, blank=True)
    religion = models.ForeignKey(Religion, on_delete=models.SET_NULL, null=True, blank=True,)
    passport = models.ImageField(upload_to='passport', blank=True, null=True)
    member_number = models.CharField(max_length=100) 


    def __str__(self):
        return f"{self.first_name} ({self.last_name})"

class Member(models.Model):
    member = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True,related_name='member')
    ippis = models.IntegerField(unique=True)  # Required and unique
    total_savings = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.member} ({self.ippis})"

    def update_total_savings(self):
        total = self.savings.aggregate(models.Sum("month_saving"))["month_saving__sum"] or 0.00

        # total = self.savings_set.aggregate(models.Sum("month_saving"))["month_saving__sum"] or 0.00
        self.total_savings = total
        self.save()

    
    # Add this method to your existing Member model
    def get_complete_financial_data(self):
        """Get complete financial data for the member"""
        
        
        # Get all savings
        savings = Savings.objects.filter(member=self).order_by('-month')
        total_savings = savings.aggregate(total=models.Sum('month_saving'))['total'] or Decimal('0.00')
        
    
        # Get all loanable
        loanable = Loanable.objects.filter(member=self).order_by('-month')
        total_loanable = loanable.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        # Get all investment
        investment = Investment.objects.filter(member=self).order_by('-month')
        total_investment = investment.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        return {
            'savings': savings,
            
            'loanable': loanable,
            'investment': investment,
            'total_savings': total_savings,
            'total_loanable': total_loanable,
            'total_investment': total_investment,
            'grand_total': total_savings  + total_loanable + total_investment
        }


   

class State(models.Model):
    title = models.CharField(max_length=50)
    # country = CountryField(blank=True, null=True)

    def __str__(self):
        return self.title

class Address(models.Model):
    user = models.OneToOneField(Member, on_delete=models.SET_NULL, null=True, blank=True)
    phone1 = models.CharField(max_length=15,null=True, blank=True)
    phone2 = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    country = CountryField(blank=True, null=True)
    state_of_origin = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    local_government_area = models.CharField(max_length=150)
    address = models.CharField(max_length=500)


    def __str__(self):
        return str(self.user)  
        

class NextOfKin(models.Model):
    user = models.OneToOneField(Member, on_delete=models.SET_NULL, null=True, blank=True)
    full_names = models.CharField(max_length=50)
    phone_no = models.CharField(max_length=15) 
    address = models.CharField(max_length=150)
    email = models.EmailField()  
    netofkin_passport = models.ImageField(upload_to='netofkin_passport', blank=True, null=True)

    def __str__(self):
        return f"{self.full_names} ({self.phone_no})"              

