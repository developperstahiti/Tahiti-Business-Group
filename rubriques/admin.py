from django.contrib import admin
from django.utils.html import format_html
from django import forms
from ads.image_utils import save_webp
from .models import ArticlePromo, ArticleInfo, ArticleNouveaute


# ── Helpers partagés ───────────────────────────────────────────────────────────

def _statut_badge(obj):
    colors = {'en_attente': '#f59e0b', 'valide': '#10b981', 'refuse': '#ef4444'}
    labels = {'en_attente': 'En attente', 'valide': 'Validé', 'refuse': 'Refusé'}
    return format_html(
        '<span style="background:{};color:#fff;padding:3px 10px;border-radius:12px;'
        'font-size:11px;font-weight:700;white-space:nowrap">{}</span>',
        colors.get(obj.statut, '#6b7280'),
        labels.get(obj.statut, obj.statut),
    )


def _photo_thumb(obj):
    if obj.photo:
        return format_html(
            '<img src="{}" style="height:38px;width:58px;object-fit:cover;'
            'border-radius:5px;border:1px solid #e5e7eb">',
            obj.photo,
        )
    return format_html('<span style="color:#9ca3af;font-size:11px">—</span>')


def _photo_preview(obj):
    if obj.photo:
        return format_html(
            '<img src="{}" style="max-height:160px;max-width:300px;border-radius:8px;'
            'border:1px solid #e5e7eb;object-fit:cover;display:block;margin-bottom:6px">'
            '<p style="font-size:11px;color:#6b7280;margin:0">Chemin : {}</p>',
            obj.photo, obj.photo,
        )
    return format_html(
        '<p style="color:#9ca3af;font-style:italic;font-size:13px">Aucune photo pour l\'instant.</p>'
    )


def _process_photo_upload(admin_instance, request, obj, form, prefix):
    """Traite l'upload de photo via save_webp et met à jour obj.photo."""
    photo_file = form.cleaned_data.get('photo_upload')
    if photo_file:
        try:
            obj.photo = save_webp(photo_file, 'rubriques', f'{prefix}_{obj.pk}')
            obj.save(update_fields=['photo'])
        except Exception as e:
            admin_instance.message_user(request, f"Erreur photo : {e}", level='warning')


# ── Formulaires avec champ upload photo ────────────────────────────────────────

class _PhotoUploadForm(forms.ModelForm):
    photo_upload = forms.ImageField(
        required=False,
        label="Charger une nouvelle photo",
        widget=forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        help_text="JPG, PNG ou WebP — max 5 Mo. Remplace la photo existante.",
    )


class ArticlePromoForm(_PhotoUploadForm):
    class Meta:
        model = ArticlePromo
        fields = '__all__'


class ArticleInfoForm(_PhotoUploadForm):
    class Meta:
        model = ArticleInfo
        fields = '__all__'


class ArticleNouveauteForm(_PhotoUploadForm):
    class Meta:
        model = ArticleNouveaute
        fields = '__all__'


# ── Admin : ArticlePromo ────────────────────────────────────────────────────────

@admin.register(ArticlePromo)
class ArticlePromoAdmin(admin.ModelAdmin):
    form = ArticlePromoForm
    list_display  = ['titre', 'pro_user', 'statut_badge', 'photo_thumb', 'created_at']
    list_filter   = ['statut']
    search_fields = ['titre', 'contenu', 'pro_user__email']
    readonly_fields = ['photo_preview', 'created_at']
    fieldsets = (
        ('Promo', {
            'fields': ('pro_user', 'titre', 'contenu', 'lien_promo', 'statut'),
        }),
        ('Photo', {
            'fields': ('photo_preview', 'photo_upload', 'photo'),
            'description': 'Uploadez une image pour illustrer la promo.',
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    actions = ['valider', 'refuser']

    def statut_badge(self, obj): return _statut_badge(obj)
    statut_badge.short_description = 'Statut'

    def photo_thumb(self, obj): return _photo_thumb(obj)
    photo_thumb.short_description = 'Photo'

    def photo_preview(self, obj): return _photo_preview(obj)
    photo_preview.short_description = 'Aperçu actuel'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _process_photo_upload(self, request, obj, form, 'promo')

    def valider(self, request, queryset):
        queryset.update(statut='valide')
        self.message_user(request, f"{queryset.count()} promo(s) validée(s).")
    valider.short_description = "Valider les articles sélectionnés"

    def refuser(self, request, queryset):
        queryset.update(statut='refuse')
        self.message_user(request, f"{queryset.count()} promo(s) refusée(s).")
    refuser.short_description = "Refuser les articles sélectionnés"


# ── Admin : ArticleInfo ─────────────────────────────────────────────────────────

@admin.register(ArticleInfo)
class ArticleInfoAdmin(admin.ModelAdmin):
    form = ArticleInfoForm
    list_display  = ['titre', 'auteur', 'statut_badge', 'photo_thumb', 'created_at']
    list_filter   = ['statut']
    search_fields = ['titre', 'contenu', 'auteur__email']
    readonly_fields = ['photo_preview', 'created_at']
    fieldsets = (
        ('Info', {
            'fields': ('auteur', 'titre', 'contenu', 'source_media', 'statut'),
        }),
        ('Photo', {
            'fields': ('photo_preview', 'photo_upload', 'photo'),
            'description': 'Uploadez une image pour illustrer l\'article.',
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    actions = ['valider', 'refuser']

    def statut_badge(self, obj): return _statut_badge(obj)
    statut_badge.short_description = 'Statut'

    def photo_thumb(self, obj): return _photo_thumb(obj)
    photo_thumb.short_description = 'Photo'

    def photo_preview(self, obj): return _photo_preview(obj)
    photo_preview.short_description = 'Aperçu actuel'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _process_photo_upload(self, request, obj, form, 'info')

    def valider(self, request, queryset):
        queryset.update(statut='valide')
        self.message_user(request, f"{queryset.count()} info(s) validée(s).")
    valider.short_description = "Valider les articles sélectionnés"

    def refuser(self, request, queryset):
        queryset.update(statut='refuse')
        self.message_user(request, f"{queryset.count()} info(s) refusée(s).")
    refuser.short_description = "Refuser les articles sélectionnés"


# ── Admin : ArticleNouveaute ────────────────────────────────────────────────────

@admin.register(ArticleNouveaute)
class ArticleNouveauteAdmin(admin.ModelAdmin):
    form = ArticleNouveauteForm
    list_display  = ['titre', 'pro_user', 'statut_badge', 'photo_thumb', 'created_at']
    list_filter   = ['statut']
    search_fields = ['titre', 'contenu', 'pro_user__email']
    readonly_fields = ['photo_preview', 'created_at']
    fieldsets = (
        ('Nouveauté', {
            'fields': ('pro_user', 'titre', 'contenu', 'lien_redirection', 'statut'),
        }),
        ('Photo', {
            'fields': ('photo_preview', 'photo_upload', 'photo'),
            'description': 'Uploadez une image pour illustrer la nouveauté.',
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    actions = ['valider', 'refuser']

    def statut_badge(self, obj): return _statut_badge(obj)
    statut_badge.short_description = 'Statut'

    def photo_thumb(self, obj): return _photo_thumb(obj)
    photo_thumb.short_description = 'Photo'

    def photo_preview(self, obj): return _photo_preview(obj)
    photo_preview.short_description = 'Aperçu actuel'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _process_photo_upload(self, request, obj, form, 'nouv')

    def valider(self, request, queryset):
        queryset.update(statut='valide')
        self.message_user(request, f"{queryset.count()} nouveauté(s) validée(s).")
    valider.short_description = "Valider les articles sélectionnés"

    def refuser(self, request, queryset):
        queryset.update(statut='refuse')
        self.message_user(request, f"{queryset.count()} nouveauté(s) refusée(s).")
    refuser.short_description = "Refuser les articles sélectionnés"
