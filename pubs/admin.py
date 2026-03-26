from django.contrib import admin
from django.utils.html import format_html
from .models import Publicite, DemandePublicite


@admin.register(Publicite)
class PubliciteAdmin(admin.ModelAdmin):
    list_display = ['titre', 'emplacement_badge', 'cat_badge', 'client_nom', 'prix_display', 'payment_badge', 'actif', 'apercu', 'created_at']
    list_filter = ['emplacement', 'categorie', 'actif', 'payment_status']
    list_editable = ['actif']
    search_fields = ['titre', 'client_nom', 'client_email', 'payment_ref']
    readonly_fields = ['created_at', 'apercu', 'payment_ref', 'payment_trans_id']
    fieldsets = (
        ('Publicité', {'fields': ('titre', 'description', 'image', 'image_url', 'lien', 'emplacement', 'categorie', 'actif')}),
        ('Client', {'fields': ('client_nom', 'client_email', 'client_tel')}),
        ('Facturation', {'fields': ('prix', 'duree_semaines', 'date_debut', 'date_fin')}),
        ('Paiement PayZen', {'fields': ('payment_status', 'payment_ref', 'payment_trans_id'), 'classes': ('collapse',)}),
        ('Aperçu', {'fields': ('apercu', 'created_at')}),
    )

    def emplacement_badge(self, obj):
        emp = obj.emplacement
        if 'billboard' in emp:
            color = '#3b82f6'
        elif 'sidebar' in emp:
            color = '#ef4444'
        elif 'strip' in emp:
            color = '#f59e0b'
        else:
            color = '#6b7280'
        label = obj.get_emplacement_display().split('(')[0].strip()
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            color, label
        )
    emplacement_badge.short_description = 'Emplacement'

    def cat_badge(self, obj):
        if not obj.categorie:
            return '—'
        cat_labels = {'vehicules': '🚗', 'immobilier': '🏠', 'occasion': '📦', 'emploi': '💼', 'services': '🔧'}
        return format_html(
            '<span style="font-weight:bold">{} {}</span>',
            cat_labels.get(obj.categorie, ''),
            obj.get_categorie_display()
        )
    cat_badge.short_description = 'Catégorie'

    def prix_display(self, obj):
        return f"{obj.prix:,} XPF".replace(',', ' ')
    prix_display.short_description = 'Prix'

    def payment_badge(self, obj):
        colors = {'paid': '#10b981', 'pending': '#f59e0b', 'failed': '#ef4444', 'expired': '#6b7280', 'none': '#d1d5db'}
        labels = {'paid': '✅ Payé', 'pending': '⏳ Attente', 'failed': '❌ Échoué', 'expired': '⏰ Expiré', 'none': '—'}
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colors.get(obj.payment_status, '#6b7280'),
            labels.get(obj.payment_status, obj.payment_status)
        )
    payment_badge.short_description = 'Paiement'

    def apercu(self, obj):
        img = obj.get_image()
        if img:
            return format_html('<img src="{}" style="max-height:80px;max-width:160px;border-radius:6px">', img)
        return format_html('<span style="color:#6b7280">Aucune image</span>')
    apercu.short_description = 'Aperçu'


@admin.register(DemandePublicite)
class DemandePubliciteAdmin(admin.ModelAdmin):
    list_display = ['nom', 'email', 'tel', 'entreprise', 'emplacement_souhaite', 'traite', 'created_at']
    list_filter = ['emplacement_souhaite', 'traite']
    list_editable = ['traite']
    search_fields = ['nom', 'email', 'entreprise']
    readonly_fields = ['created_at']
    actions = ['marquer_traite']

    def marquer_traite(self, request, queryset):
        queryset.update(traite=True)
        self.message_user(request, f"{queryset.count()} demande(s) marquée(s) traitée(s).")
    marquer_traite.short_description = "Marquer comme traitée"
