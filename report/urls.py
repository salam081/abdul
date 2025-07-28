from django.urls import path
# from .views import ReportingDashboardView
from .import views


urlpatterns = [
   path('loan/reports/', views.admin_loan_reports, name='admin_loan_reports'),
   path('loan_request_report', views.loan_request_report, name='loan_request_report'),
   path("loan-repayments/", views.filtered_loan_repayments, name="filtered_loan_repayments"),
    
    # path('consumable_report_dashboard/', ReportingDashboardView.as_view(), name='consumable_report_dashboard'),
    path('request_status_report',views.request_status_report,name='request_status_report'),
    path('user_spending_report',views.user_spending_report,name='user_spending_report'),
    path('payment_analysis_report',views.payment_analysis_report,name='payment_analysis_report'),
    path('approval_workflow_report',views.approval_workflow_report,name='approval_workflow_report'),
]
