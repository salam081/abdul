from django.urls import path
from .import views

urlpatterns = [
    path('requests-disabled/',views. disabled_requests_page, name='disabled_requests_page'),
    path('member_dashboard',views.member_dashboard,name="member_dashboard"),
    # path('loan_request/', views.loan_request_view, name='loan_request'),
    path('loan-request/', views.loan_request_view, name='loan_request'),
    path('guarantor/<int:pk>/', views.show_guarantor_approval, name='guarantor_approval_page'),
    path('guarantor/confirm/<int:pk>/', views.confirm_guarantor_approval, name='confirm_guarantor_approval'),
    path('ajax/load-bank-code/', views.ajax_load_bank_code, name='ajax_load_bank_code'),
    path('member_request_consumable/', views.member_request_consumable, name='member_request_consumable'),
    path('edit-request/<int:request_id>/', views.edit_consumable_request, name='edit_consumable_request'),
    path('member_savings',views.member_savings,name='member_savings'),
    path('my_loan_requests/', views.my_loan_requests, name='my_loan_requests'),
    path('loan_details/<int:request_id>/', views.member_loan_request_detail, name='member_loan_request_detail'),
    path('my-requests/', views.my_consumable_requests, name='my_consumable_requests'),
    path('request/<int:request_id>/', views.consumable_request_detail, name='consumable_request_detail'),
    path('consumables/cancel/<int:request_id>/', views.cancel_consumable_request, name='cancel_consumable_request'),


   
    
]