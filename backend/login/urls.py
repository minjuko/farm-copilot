
from django.urls import path
from . import views

app_name = 'login'

urlpatterns = [
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('check_username/', views.check_username, name='check_username'),
    path('send_verification_email/', views.send_verification_email, name='send_verification_email'),
    path('password-reset/', views.password_reset_page, name='password_reset'),
    path('password_reset/', views.password_reset_request, name='password_reset_request'),
    path('password_reset_confirm/', views.password_reset, name='password_reset_confirm_api'),
    path('signup/', views.signup, name='signup'),
    path('auth_check/', views.auth_check, name='auth_check'),
    path('change_password/', views.change_password, name='change_password'),
    path('change_username/', views.change_username, name='change_username'),
    path('delete_account/', views.delete_account, name='delete_account')
]
