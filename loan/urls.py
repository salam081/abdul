from django.urls import path 
from .import views

urlpatterns = [
    path('loan/settings/', views.admin_loan_settings, name='admin_loan_settings'),
    path('loan-type/add/', views.add_loan_type, name='add_loan_type'),
    path('admin_loan_requests_list', views.admin_loan_requests_list, name='admin_loan_requests'),
    path('loan_request_detail/<str:id>/',views.loan_request_detail, name='loan_request_detail'),
    path('add_single_loan_payment', views.add_single_loan_payment, name='add_single_loan_payment'),
    path("ajax/get-loan-types/", views.get_loan_types_for_year, name="get_loan_types_for_year"),
    path('upload_loan_payment/', views.upload_loan_payment, name='upload_loan_payment'),
    # path('requested_loan',views.get_all_requested_loan, name='requested_loan'),
    path('payslip_img_details/<str:id>',views.payslip_img_details, name='payslip_img_details'),
    path('edit_requested_loan/<str:id>/',views.edit_requested_loan,name='edit_requested_loan'),
    path('approve_loan_request/<str:id>/',views.approve_loan_request,name='approve_loan_request'),
    path('reject-loan-request/<int:id>/', views.reject_loan_request, name='reject_loan_request'),
    path('all_reject_loan', views.all_reject_loan, name='all_reject_loan'),
    path('delete_reject_loan/<str:id>/', views.delete_reject_loan, name='delete_reject_loan'),
    # path('loan-type/delete/<int:pk>/', views.delete_loan_type, name='delete_loan_type'),
    path('loan_years_list/', views.loan_years_list, name='loan_years_list'),
    path('loans_by_year/<int:year>/<str:loan_type_filter>/', views.loans_by_year, name='loans_by_year'),
    path('loan_fee',views.loan_fee,name="loan_fee"),
   path('loan/repayments/', views.admin_repayment_tracking, name='admin_repayment_tracking'),
    
]