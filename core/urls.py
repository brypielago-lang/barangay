from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
urlpatterns = [
    path('', views.dashboard, name='dashboard'), path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'), path('logout/', auth_views.LogoutView.as_view(), name='logout'), path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'), path('requests/new/', views.request_create, name='request_create'), path('requests/<int:pk>/', views.request_detail, name='request_detail'), path('requests/<int:pk>/document/', views.certificate_pdf, name='certificate_pdf'),
    path('staff/requests/', views.staff_requests, name='staff_requests'), path('staff/requests/<int:pk>/update/', views.update_request, name='update_request'), path('reports/', views.reports, name='reports'), path('reports/export/', views.report_csv, name='report_csv'),
    path('notifications/', views.notifications, name='notifications'), path('verify/<uuid:token>/', views.verify, name='verify'), path('qr/<uuid:token>/', views.qr_code, name='qr_code'),
]
