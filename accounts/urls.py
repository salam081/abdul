from django.urls import path
from .import views
urlpatterns = [
    path("",views.login_view,name='login'),
    path("member_check",views.member_check,name='member_check'),
    path("logout",views.logout_view,name='logout'),
    path("upload_users/",views.upload_users,name='upload_users'),
    path("complete_profile/",views.complete_profile,name='complete_profile'),
    path("register",views.user_registration,name='register'),
    path("all_members",views.all_members,name='all_members'),
    path("delete_member/<str:id>/",views.delete_member,name='delete_member'),
    path("deactivate_users",views.deactivate_users,name='deactivate_users'),
    path('activate-users/', views.activate_users, name='activate_users'),
    # path("address/<int:id>/", views.create_or_update_address, name="create_or_update_address"),
    # path("next-of-kin/<int:id>/", views.create_or_update_next_of_kin, name="create_or_update_next_of_kin"),
    path("member/<int:id>/", views.member_detail, name="member_detail"),
    path("admin_members/<int:id>/", views.admin_member_detail, name="admin_member_detail"),

    path('reset_password_view/<int:id>/', views.reset_password_view, name='reset_password'),
    path('changePassword', views.changePassword, name='change_password'),
    path('add_user_to_group/<int:id>/', views.add_user_to_group, name='add_user_to_group'),

     path('delete-users/', views.delete_non_superusers),

]