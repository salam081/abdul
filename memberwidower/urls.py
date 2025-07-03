# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # path("submit_widower_request", views.submit_widower_request, name="submit_widower_request"),
    # path("approve_widower_requests/", views.approve_widower_requests, name="approve_widower_requests"),
    path("cooperative_summary/", views.cooperative_summary, name="cooperative_summary"),
   
    path('list_withdrawal_requests/', views.list_withdrawal_requests, name='list_withdrawal_requests'),
    path('member_withdrawal_request', views.member_withdrawal_request, name='member_withdrawal_request'),
    path('approve/<int:pk>/', views.approve_withdrawal_request, name='approve_withdrawal_request'),
    path('decline/<int:pk>/', views.decline_withdrawal_request, name='decline_withdrawal_request'),
    path('eligible-members/', views.eligible_members_view, name='eligible_members_view'),
    
]
