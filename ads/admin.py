from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse
import csv
from .models import Annonce, Message, Signalement, AlerteAnnonce, Enregistrement


def _export_csv(modeladmin, request, queryset):
    """Action admin : exporte la sélection en CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{queryset.model.__name__}.csv"'
    writer = csv.writer(response)
    fields = [f.name for f in queryset.model._meta.fields]
    writer.writerow(fields)
    for obj in queryset:
        writer.writerow([getattr(obj, f) for f in fields])
    return response
_export_csv.short_description = "Exporter en CSV"


@admin.register(Annonce)
class AnnonceAdmin(admin.ModelAdmin):
    list_display = ['titre', 'user', 'categorie', 'prix_display', 'statut_badge', 'verified_badge', 'views', 'boost', 'created_at']
    list_filter = ['statut', 'categorie', 'boost', 'verified', 'created_at']
    search_fields = ['titre', 'description', 'user__email', 'user__nom']
    list_editable = ['boost']
    actions = ['approuver', 'moderer', 'marquer_vendu', 'marquer_verifie', _export_csv]
    readonly_fields = ['views', 'created_at', 'updated_at', 'photos_preview']
    fieldsets = (
        ('Annonce', {'fields': ('titre', 'categorie', 'prix', 'prix_unite', 'prix_label', 'localisation', 'description')}),
        ('Média', {'fields': ('photos', 'photos_preview')}),
        ('Statut', {'fields': ('statut', 'boost', 'verified', 'user')}),
        ('Stats', {'fields': ('views', 'created_at', 'updated_at')}),
    )

    def prix_display(self, obj):
        return obj.get_prix_display_label()
    prix_display.short_description = 'Prix'

    def statut_badge(self, obj):
        colors = {'actif': '#00e687', 'modere': '#f59e0b', 'vendu': '#6b7280', 'expire': '#ef4444'}
        color = colors.get(obj.statut, '#6b7280')
        return format_html(
            '<span style="background:{};color:#000;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color, obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'

    def verified_badge(self, obj):
        if obj.verified:
            return format_html('<span style="color:#059669;font-weight:bold">✓</span>')
        return ''
    verified_badge.short_description = 'Vérifiée'
    verified_badge.admin_order_field = 'verified'

    def photos_preview(self, obj):
        if not obj.photos:
            return 'Aucune photo'
        imgs = ''.join(
            f'<img src="{p}" style="height:60px;margin:2px;border-radius:4px">' for p in obj.photos[:4]
        )
        return format_html(imgs)
    photos_preview.short_description = 'Aperçu photos'

    def approuver(self, request, queryset):
        queryset.update(statut='actif')
        self.message_user(request, f"{queryset.count()} annonce(s) approuvée(s).")
    approuver.short_description = "Approuver les annonces sélectionnées"

    def moderer(self, request, queryset):
        queryset.update(statut='modere')
        self.message_user(request, f"{queryset.count()} annonce(s) modérée(s).")
    moderer.short_description = "Modérer les annonces sélectionnées"

    def marquer_vendu(self, request, queryset):
        queryset.update(statut='vendu')
        self.message_user(request, f"{queryset.count()} annonce(s) marquée(s) vendue.")
    marquer_vendu.short_description = "Marquer comme vendu"

    def marquer_verifie(self, request, queryset):
        queryset.update(verified=True)
        self.message_user(request, f"{queryset.count()} annonce(s) marquée(s) vérifiée(s).")
    marquer_verifie.short_description = "Marquer comme vérifiée"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['annonce', 'from_user', 'to_user', 'read', 'created_at']
    list_filter = ['read', 'created_at']
    search_fields = ['from_user__email', 'to_user__email', 'content', 'annonce__titre']
    readonly_fields = ['created_at']
    actions = ['marquer_lu']

    def marquer_lu(self, request, queryset):
        queryset.update(read=True)
    marquer_lu.short_description = "Marquer comme lu"

@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):
    list_display  = ['annonce', 'raison', 'auteur', 'created_at']
    list_filter   = ['raison', 'created_at']
    search_fields = ['annonce__titre', 'details']
    readonly_fields = ['created_at']
    actions = ['supprimer_annonce_signalee']

    def supprimer_annonce_signalee(self, request, queryset):
        for s in queryset:
            s.annonce.statut = 'modere'
            s.annonce.save()
        self.message_user(request, f"{queryset.count()} annonce(s) modérée(s).")
    supprimer_annonce_signalee.short_description = "Modérer l'annonce signalée"


@admin.register(Enregistrement)
class EnregistrementAdmin(admin.ModelAdmin):
    list_display = ['user', 'annonce', 'date_creation']
    list_filter = ['date_creation']
    search_fields = ['user__email', 'user__nom', 'annonce__titre']
    readonly_fields = ['date_creation']


@admin.register(AlerteAnnonce)
class AlerteAnnonceAdmin(admin.ModelAdmin):
    list_display = ['user', 'categorie', 'sous_categorie', 'derniere_notification', 'created_at']
    list_filter = ['categorie']
    search_fields = ['user__email', 'user__nom']
    readonly_fields = ['created_at']
