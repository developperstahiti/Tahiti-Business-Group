from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from django.urls import reverse

CATEGORIES = [
    ('vehicules',    'Véhicules'),
    ('immobilier',   'Immobilier'),
    ('occasion',     'Occasion / Bon Plan'),
    ('emploi',       'Offre et Demande d\'emploi'),
    ('services',     'Service / Prestation'),
]

STATUTS = [
    ('actif',  'Actif'),
    ('modere', 'Modéré'),
    ('vendu',  'Vendu'),
    ('expire', 'Expiré'),
]

BOOST_DUREE_CHOICES = [
    ('',       'Sans boost'),
    ('7jours', '7 jours (payant)'),
    ('1mois',  '1 mois (payant)'),
]

# Sous-catégories style Leboncoin — source unique de vérité
SOUS_CATEGORIES = {
    'immobilier': [
        ('immo-appartements', 'Appartements et studios'),
        ('immo-maisons',      'Maisons et villas'),
        ('immo-terrains',     'Terrains et lots'),
        ('immo-bureaux',      'Bureaux et commerces'),
        ('immo-saisonnieres', 'Saisonnières'),
        ('immo-parkings',     'Parkings et garages'),
    ],
    'vehicules': [
        ('vehicules-voitures',    'Voitures'),
        ('vehicules-2roues',      'Motos et scooters'),
        ('vehicules-bateaux',     'Bateaux et jet-skis'),
        ('vehicules-utilitaires', 'Utilitaires et camions'),
        ('vehicules-pieces',      'Pièces et accessoires'),
    ],
    'occasion': [
        ('occasion-telephones',     'Téléphones'),
        ('occasion-informatique',   'Informatique'),
        ('occasion-tv',             'TV et Audio'),
        ('occasion-jeux-video',     'Jeux vidéo'),
        ('occasion-electromenager', 'Électroménager'),
        ('occasion-meubles',        'Meubles et Déco'),
        ('occasion-vetements',      'Vêtements'),
        ('occasion-sport',          'Sport et Loisirs'),
        ('occasion-puericulture',   'Puériculture'),
        ('occasion-jouets',         'Jouets'),
        ('occasion-divers',         'Divers'),
    ],
    'emploi': [
        ('emploi-offre',     'Offre d\'emploi'),
        ('emploi-recherche', 'Recherche d\'emploi'),
    ],
    'services': [
        ('services-travaux',   'Travaux et BTP'),
        ('services-cours',     'Cours et Formation'),
        ('services-transport', 'Transport'),
        ('services-sante',     'Santé et Beauté'),
        ('services-jardinage', 'Jardinage'),
        ('services-autres',    'Autres services'),
    ],
}

SOUS_CATEGORIE_CHOICES = [item for sublist in SOUS_CATEGORIES.values() for item in sublist]

PRIX_UNITE_CHOICES = [
    ('',         '— Prix fixe'),
    ('heure',    '/ heure'),
    ('jour',     '/ jour'),
    ('semaine',  '/ semaine'),
    ('mois',     '/ mois'),
    ('unite',    '/ unité'),
    ('negocier', 'À négocier'),
]


class Annonce(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='annonces'
    )
    titre          = models.CharField(max_length=200)
    description    = models.TextField()
    prix           = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    prix_label     = models.CharField(max_length=50, blank=True, help_text="Ex: 15 000 XPF, Prix sur demande, À débattre")
    prix_unite     = models.CharField(max_length=20, choices=PRIX_UNITE_CHOICES, default='', blank=True)
    categorie      = models.CharField(max_length=50, choices=CATEGORIES)
    sous_categorie = models.CharField(max_length=50, blank=True, default='')
    type_transaction = models.CharField(
        max_length=20,
        choices=[('non_applicable', 'Non applicable'), ('vente', 'Vente'), ('location', 'Location')],
        default='non_applicable',
    )
    localisation   = models.CharField(max_length=100, default='', blank=True)  # ancien champ — compatibilite
    commune        = models.CharField(max_length=100, blank=True, default='')
    quartier       = models.CharField(max_length=100, blank=True, default='')
    precision_lieu = models.CharField(max_length=150, blank=True, default='')
    photos         = models.JSONField(default=list, blank=True)
    specs          = models.JSONField(default=dict, blank=True)
    statut         = models.CharField(max_length=20, choices=STATUTS, default='actif')
    boost            = models.BooleanField(default=False)
    boost_duree      = models.CharField(max_length=20, choices=BOOST_DUREE_CHOICES, default='', blank=True)
    boost_demande    = models.TextField(blank=True, default='')
    boost_status     = models.CharField(
        max_length=20, blank=True, default='',
        choices=[('', 'Sans boost'), ('active', 'Actif'), ('pending', 'En attente'), ('expired', 'Expiré')]
    )
    boost_expires_at = models.DateTimeField(null=True, blank=True)
    boost_payment_ref = models.CharField(max_length=30, blank=True, default='')
    slug           = models.SlugField(max_length=200, blank=True, default='')
    verified       = models.BooleanField(default=False)
    views          = models.PositiveIntegerField(default=0)  # impressions (vu a l'ecran)
    clics          = models.PositiveIntegerField(default=0)  # clics (ouverture detail)
    derniere_remontee = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Annonce'
        verbose_name_plural = 'Annonces'
        ordering = ['-boost', '-created_at']
        indexes = [
            models.Index(fields=['statut'], name='idx_annonce_statut'),
            models.Index(fields=['categorie'], name='idx_annonce_categorie'),
            models.Index(fields=['statut', 'categorie'], name='idx_annonce_stat_cat'),
            models.Index(fields=['-created_at'], name='idx_annonce_created'),
        ]

    def __str__(self):
        return self.titre

    def save(self, *args, **kwargs):
        # Si update_fields est specifie sans 'slug', on ne regenere pas le slug
        # (ex: increment_clics appelle save(update_fields=['clics']))
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and 'slug' not in update_fields:
            super().save(*args, **kwargs)
            return

        # On doit d'abord sauvegarder pour avoir un pk (creation)
        if not self.pk:
            super().save(*args, **kwargs)
            # Apres la premiere sauvegarde, on genere le slug avec le pk
            self.slug = f"{slugify(self.titre)}-{self.pk}"
            super().save(update_fields=['slug'])
        else:
            # Mise a jour : regenerer le slug si le titre a change
            self.slug = f"{slugify(self.titre)}-{self.pk}"
            super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('annonce_detail', kwargs={'pk': self.pk, 'slug': self.slug})

    def get_prix_display_label(self):
        if self.prix_label:
            return self.prix_label
        if self.prix_unite == 'negocier':
            return 'À négocier'
        if self.prix == 0:
            return 'Prix sur demande'
        base = f"{self.prix:,} XPF".replace(',', '\u00a0')
        if self.prix_unite:
            unite_map = dict(PRIX_UNITE_CHOICES)
            return f"{base} {unite_map.get(self.prix_unite, '')}"
        return base

    def get_main_photo(self):
        return self.photos[0] if self.photos else None

    def increment_clics(self):
        """Incrémente le compteur de clics."""
        self.clics += 1
        self.save(update_fields=['clics'])


class Message(models.Model):
    annonce   = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name='messages')
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    to_user   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages',
    )
    content    = models.TextField(max_length=1000)
    read       = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['to_user', 'read', 'created_at'], name='idx_msg_unread'),
        ]

    def __str__(self):
        return f"Message {self.from_user} → {self.to_user} ({self.annonce.titre})"


class Signalement(models.Model):
    RAISONS = [
        ('spam',    'Spam / Annonce en double'),
        ('arnaque', 'Arnaque / Fraude'),
        ('illegal', 'Contenu illégal ou choquant'),
        ('autre',   'Autre'),
    ]
    annonce    = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name='signalements')
    auteur     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True)
    raison     = models.CharField(max_length=20, choices=RAISONS)
    details    = models.TextField(blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Signalement'
        verbose_name_plural = 'Signalements'

    def __str__(self):
        return f"Signal #{self.pk} — {self.annonce.titre}"


class Notation(models.Model):
    vendeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notations_recues',
    )
    acheteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notations_donnees',
    )
    note = models.IntegerField()  # 1 à 5
    avis_ecrit = models.TextField(blank=True, default='', max_length=500)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notation'
        verbose_name_plural = 'Notations'
        unique_together = ['acheteur', 'vendeur']
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.acheteur} → {self.vendeur} : {self.note}/5"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.acheteur_id == self.vendeur_id:
            raise ValidationError("Un utilisateur ne peut pas se noter lui-même.")
        if self.note < 1 or self.note > 5:
            raise ValidationError("La note doit être comprise entre 1 et 5.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Enregistrement(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enregistrements',
    )
    annonce = models.ForeignKey(
        'Annonce',
        on_delete=models.CASCADE,
        related_name='enregistrements',
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Enregistrement'
        verbose_name_plural = 'Enregistrements'
        unique_together = ('user', 'annonce')

    def __str__(self):
        return f"{self.user} — {self.annonce.titre}"


class AlerteAnnonce(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alertes'
    )
    categorie      = models.CharField(max_length=50, choices=CATEGORIES)
    sous_categorie = models.CharField(max_length=50, blank=True, default='')
    derniere_notification = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Alerte annonce'
        verbose_name_plural = 'Alertes annonces'
        unique_together = ['user', 'categorie', 'sous_categorie']

    def __str__(self):
        return f"Alerte {self.user} — {self.categorie}"
