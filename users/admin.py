from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'nom', 'role_badge', 'tel', 'abonnement_promo_actif', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'nom', 'tel']
    ordering = ['-date_joined']
    readonly_fields = ['date_joined']

    fieldsets = (
        ('Identifiants', {'fields': ('email', 'password')}),
        ('Infos personnelles', {'fields': ('nom', 'tel', 'whatsapp', 'avatar')}),
        ('Compte Pro', {'fields': ('nom_entreprise', 'numero_tahiti', 'abonnement_promo_actif')}),
        ('Rôle & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom', 'role', 'password1', 'password2'),
        }),
    )

    def role_badge(self, obj):
        colors = {'admin': '#ef4444', 'pro': '#1a6cf1', 'personnel': '#00e687'}
        color = colors.get(obj.role, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Rôle'