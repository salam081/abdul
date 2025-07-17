from django.urls import path
from .import views
urlpatterns = [
    path('purchase_consumable_dashboard', views.purchase_consumable_dashboard,name='purchase_consumable_dashboard'),
    path('consumable_purchase_request_create', views.consumable_purchase_request_create,name='consumable_purchase_request_create'),
    path('consumable_purchase_request_create', views.consumable_purchase_request_create,name='consumable_purchase_request_create'),
    path('purchase_request_list', views.purchase_request_list,name='purchase_request_list'),
    path('consumable_purchase_request_detail/<pk>/', views.consumable_purchase_request_detail,name='consumable_purchase_request_detail'),
    path('purchase_consumable_request_update/<pk>/', views.purchase_consumable_request_update,name='purchase_consumable_request_update'),
    path('consumable_purchase_request_delete/<pk>/', views.consumable_purchase_request_delete,name='consumable_purchase_request_delete'),
    path('consumable_purchase_request_approve/<pk>/', views.consumable_purchase_request_approve,name='consumable_purchase_request_approve'),
    path('purchased_item_create/<request_pk>/', views.purchased_item_create,name='purchased_item_create'),
    path('consumable_request_mark_accounted/<pk>/', views.consumable_request_mark_accounted,name='consumable_request_mark_accounted'),
    
    
    path('selling-plans/', views.selling_plan_list, name='selling_plan_list'),
    path("selling_plan_create/<int:pk>/", views.selling_plan_create, name="selling_plan_create"),
    path('selling_plan_detail/<int:pk>/', views.selling_plan_detail, name='selling_plan_detail'),
    path('selling_plan_update/<int:pk>/', views.selling_plan_update, name='selling_plan_update'),
    path('selling_plan_delete/<int:pk>/', views.selling_plan_delete, name='selling_plan_delete'),

]