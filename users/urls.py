from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
import logging

logger = logging.getLogger(__name__)


class SafePasswordResetView(auth_views.PasswordResetView):
    """Redirige vers 'done' meme si l'envoi SMTP echoue."""
    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception as e:
            logger.error("Erreur envoi email reset: %s", e)
            return super(auth_views.PasswordResetView, self).form_valid(form)


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('mon-compte/', views.mon_compte, name='mon_compte'),
    path('upgrade-pro/', views.upgrade_to_pro, name='upgrade_to_pro'),
    path('c01e87364339aac/', views.admin_dashboard, name='admin_dashboard'),
    path('c01e87364339aac/moderer/<int:pk>/', views.moderer_annonce, name='moderer_annonce'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    path('supprimer-compte/', views.supprimer_compte, name='supprimer_compte'),
    path('test-email/', views.test_email, name='test_email'),

    # Password reset
    path('password-reset/', SafePasswordResetView.as_view(
        template_name='users/password_reset.html',
        html_email_template_name='emails/password_reset_email.html',
        subject_template_name='emails/password_reset_subject.txt',
        success_url='/users/password-reset/done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html',
        success_url='/users/reset/done/',
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html',
    ), name='password_reset_complete'),
]