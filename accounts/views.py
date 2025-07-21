from django.shortcuts import render,redirect,get_object_or_404
from django_countries import countries
from django.contrib import messages
from.models import *
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.core.paginator import Paginator
import pandas as pd
from decimal import Decimal
from django.db import transaction
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.shortcuts import redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from datetime import datetime
from accounts.models import Address, NextOfKin 
from accounts.models import User, Member, Gender
from django.db import transaction
import os


# @staff_member_required
def delete_non_superusers(request):
    # User = get_user_model()
    # Member.objects.all().delete()
    # User.objects.filter(is_superuser=False).delete()
    return HttpResponse("All non-superuser users deleted.")

def member_check(request):
    if request.method == 'POST':
        ippis = request.POST.get("ippis")
        if Member.objects.filter(ippis=ippis).exists():
            messages.error(request, "This  code is already taken.")
            return redirect("member_check")
        else:
            messages.success(request, f" member with, code {ippis} have Not being Taking")

            return redirect("register")

    return render(request,'accounts/member_check.html')


@login_required
def upload_users(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        df = pd.read_excel(excel_file)

        required_columns = [
            "username", "first_name", "last_name", "other_name",
            "date_of_birth", "department",
            "member_number", "ippis", "group"
        ]
        # Ensure all required columns exist
        if not all(col in df.columns for col in required_columns):
            messages.error(request, "Missing one or more required columns.")
            return redirect("upload_users")

        users_to_create = []
        ippis_to_user = []

        existing_usernames = set(User.objects.values_list("username", flat=True))
        existing_ippis = set(Member.objects.values_list("ippis", flat=True))

        for _, row in df.iterrows():
            username = str(row["username"]).strip()
            ippis = int(row["ippis"]) if pd.notna(row["ippis"]) else None

            if username in existing_usernames or ippis in existing_ippis:
                continue

            group_title = str(row.get("group", "")).strip()
            try:
                user_group = UserGroup.objects.get(title__iexact=group_title)
            except UserGroup.DoesNotExist:
                messages.error(request, f"Group '{group_title}' not found.")
                return redirect("upload_users")



            user = User(
                username=username,
                first_name=row.get("first_name", "").strip(),
                last_name=row.get("last_name", "").strip(),
                other_name=row.get("other_name", "").strip(),
                date_of_birth=row.get("date_of_birth") if pd.notna(row.get("date_of_birth")) else None,
                department=row.get("department", "").strip(),
                group=user_group,
                member_number=row.get("member_number", "").strip(),
                # password=hashed_password,  # Set the hashed password
            )
            users_to_create.append(user)
            ippis_to_user.append(ippis)

        with transaction.atomic():
            created_users = User.objects.bulk_create(users_to_create)
            
            # Set default password for all created users
            User.objects.filter(id__in=[user.id for user in created_users]).update(
                password=make_password("default123")
            )

            members = [
                Member(member=user, ippis=ippis)
                for user, ippis in zip(created_users, ippis_to_user)
                if ippis is not None
            ]
            Member.objects.bulk_create(members)

        added_count = len(created_users)
        skipped_count = len(df) - added_count
        messages.success(request, f"{added_count} members successfully added, {skipped_count} skipped.")
        return redirect("upload_users")

    return render(request, "accounts/upload_users.html")

@login_required
def complete_profile(request):
    user = request.user

    if request.method == 'POST':
        # Update user fields
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.other_name = request.POST.get('other_name', user.other_name)
        user.date_of_birth = request.POST.get('date_of_birth') or None
        user.department = request.POST.get('department', user.department)
        user.group_id = request.POST.get('group') or user.group_id
        user.save()

        # Create or update address using update_or_create
        country = request.POST.get("country")
        state_of_origin_id = request.POST.get("state_of_origin") or None
        local_government_area = request.POST.get("local_government_area")
        full_address = request.POST.get("address")

        Address.objects.update_or_create(
            user=user,
            defaults={
                'country': country,
                'local_government_area': local_government_area,
                'state_of_origin_id': state_of_origin_id,
                'address': full_address,
            }
        )

        # Create or update next of kin using update_or_create
        full_names = request.POST.get("kin_full_names")
        phone_no = request.POST.get("kin_phone_no")
        kin_address = request.POST.get("kin_address")
        email = request.POST.get("kin_email")

        NextOfKin.objects.update_or_create(
            user=user,
            defaults={
                'full_names': full_names,
                'phone_no': phone_no,
                'address': kin_address,
                'email': email,
            }
        )

        messages.success(request, "Profile completed successfully.")
        return redirect('member_dashboard')

    context = {
        'genders': Gender.objects.all(),
        'marital_statuses': MaritalStatus.objects.all(),
        'religions': Religion.objects.all(),
        'user': user,
    }
    return render(request, 'accounts/complete_profile.html', context)


def user_registration(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        other_name = request.POST.get("other_name")
        username = request.POST.get("username", "").strip().lower()
        date_of_birth = request.POST.get("date_of_birth")
        department = request.POST.get("department")
        unit = request.POST.get("unit")
        gender_id = request.POST.get("gender") 
        passport = request.FILES.get("passport") 
        ippis = request.POST.get("ippis")
        savings = request.POST.get("savings")
        member_number = request.POST.get("member_number")

        if Member.objects.filter(ippis=ippis).exists():
            messages.error(request, "This student code is already taken.")
            return redirect("register")

        try:
            user_group = UserGroup.objects.get(title='members')
        except UserGroup.DoesNotExist:
            messages.error(request, "User group 'members' not found.")
            return redirect("register")

        # If Gender is a ForeignKey:
        gender_instance = Gender.objects.get(id=gender_id) if gender_id else None

        user = User.objects.create(
            first_name=first_name,
            last_name=last_name,
            other_name=other_name,
            username=username,
            savings=savings,
            date_of_birth=date_of_birth,
            department=department,
            member_number=member_number,
            unit=unit,
            group=user_group,
            is_active=True,
            passport=passport, 
            gender=gender_instance  
        )

        user.set_password("pass")
        user.save()

        Member.objects.create(
            member=user,
            ippis=ippis,
            total_savings=0
        )

        messages.success(request, "Registration successful! Default password is 'pass'.")
        return redirect('all_members')

    genders = Gender.objects.all()  
    return render(request, "accounts/user_register.html", {"genders": genders})




def is_profile_complete(user):
    required_fields = ['first_name', 'last_name', 'other_name', 'date_of_birth', 'department', 'group']
    for field in required_fields:
        if not getattr(user, field, None):
            return False
    # Check if Address and NextOfKin exist for user
    if not Address.objects.filter(user=user).exists():
        return False
    if not NextOfKin.objects.filter(user=user).exists():
        return False
    return True

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back {user.username}')

            if user.group and user.group.title.lower() == 'admin':
                return redirect('admin_dashboard')

            elif user.group and user.group.title.lower() == 'members':
                # Redirect to complete_profile if profile is not complete
                if not is_profile_complete(user):
                    return redirect('complete_profile')
                return redirect('member_dashboard')

            elif user.group and user.group.title.lower() == 'staff':
                return redirect('admin_dashboard')

            else:
                return redirect('login')
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('login')

    return render(request, 'accounts/login.html')




def logout_view(request):
    logout(request) 
    messages.success(request, "You have been logged out.")
    return redirect('login')


def all_members(request):
    members_list = User.objects.all()
    paginator = Paginator(members_list, 150)  # Show 10 members per page

    page_number = request.GET.get("page")
    members = paginator.get_page(page_number)

    return render(request, "accounts/all_members.html", {"members": members})


def member_detail(request, id):
    member = get_object_or_404(User, id=id)
    address = getattr(member, 'address', None)
    next_of_kin = getattr(member, 'nextofkin', None)

    context = {"member": member, "address": address, "next_of_kin": next_of_kin}
    return render(request, "accounts/member_detail.html", context)


@login_required
def deactivate_users(request):
    if request.method == 'POST':
        user_ids = request.POST.getlist('user_ids')
        if user_ids:
            users_to_deactivate: QuerySet[User] = User.objects.filter(id__in=user_ids)
            updated_count = users_to_deactivate.update(is_active=False)
            messages.success(request, f"{updated_count} user(s) have been deactivated.")
        else:
            messages.warning(request, "No users were selected for deactivation.")
        return redirect('all_members')
    return redirect('all_members')

@login_required
def activate_users(request):
    if request.method == 'POST':
        user_ids = request.POST.getlist('user_ids')

        # If form was submitted via JavaScript into one input (comma-separated)
        if len(user_ids) == 1 and ',' in user_ids[0]:
            user_ids = user_ids[0].split(',')

        # Filter out empty strings and convert to integers
        user_ids = [int(uid) for uid in user_ids if uid.strip().isdigit()]

        if user_ids:
            users_to_activate = User.objects.filter(id__in=user_ids)
            updated_count = users_to_activate.update(is_active=True)
            messages.success(request, f"{updated_count} user(s) have been activated.")
        else:
            messages.warning(request, "No valid users were selected for activation.")

        return redirect('all_members')

    return redirect('all_members')

def changePassword(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        if not request.user.check_password(old_password):
            messages.error(request, 'Old password is incorrect')
            return redirect('change_password')
        elif new_password1 != new_password2:
            messages.error(request, 'New passwords do not match')
            return redirect('change_password')
        else:
            request.user.set_password(new_password1)
            request.user.save()
            messages.success(request, 'Password successfully changed login ')
            return redirect('login')

    return render(request, 'accounts/change_password.html')

@login_required
def resetPassword(request,id):
    user = User.objects.get(id=id)
    user.set_password("pass")
    user.save()
    # PasswordResetLog.objects.create(reset_by=request.user,reset_for=user)

    messages.success(request, "Password reset successful!")
    return redirect('all_members')

