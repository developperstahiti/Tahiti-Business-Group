from django.db import models
from django.conf import settings

CATEGORIES = [
    ('vehicules',    'Véhicules'),
    ('immobilier',   'Immobilier'),
    ('occasion',     'Occasion'),
    ('emploi',       'Emploi'),
    ('services',     'Services'),
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
    'vehicules': [
        ('vehicules-4x4',         'Voitures / 4 roues'),
        ('vehicules-2roues',      '2 roues (scooters/motos)'),
        ('vehicules-bateaux',     'Bateaux & jet-skis'),
        ('vehicules-utilitaires', 'Utilitaires & camions'),
        ('vehicules-pieces',      'Pièces auto & accessoires'),
    ],
    'immobilier': [
        ('immo-appartements', 'Appartements & studios'),
        ('immo-maisons',      'Maisons & villas'),
        ('immo-terrains',     'Terrains & lots'),
        ('immo-bureaux',      'Bureaux & commerces'),
        ('immo-saisonnieres', 'Saisonnières (Arue/Papeete)'),
        ('immo-parkings',     'Parkings & garages'),
    ],
    'occasion': [
        ('occasion-telephones',     'Téléphones & accessoires'),
        ('occasion-ordinateurs',    'Ordinateurs & tablettes'),
        ('occasion-pc',             'PC & Informatique'),
        ('occasion-tv',             'TV & Audio'),
        ('occasion-jeux-video',     'Jeux vidéo'),
        ('occasion-electromenager', 'Électroménager'),
        ('occasion-meubles',        'Meubles & Déco'),
        ('occasion-vetements',      'Vêtements & Mode'),
        ('occasion-sport',          'Sport & Loisirs'),
        ('occasion-puericulture',   'Puériculture'),
        ('occasion-jeux-jouets',    'Jeux & Jouets'),
        ('occasion-divers',         'Divers'),
    ],
    'emploi': [
        ('emploi-commerciaux',  'Commerciaux'),
        ('emploi-informatique', 'Informatique & Dév'),
        ('emploi-hotellerie',   'Hôtellerie & Resto'),
        ('emploi-btp',          'BTP & Construction'),
        ('emploi-services',     'Services à la personne'),
    ],
    'services': [
        ('services-travaux',   'Travaux & BTP'),
        ('services-cours',     'Cours & Formation'),
        ('services-transport', 'Transport'),
        ('services-sante',     'Santé & Beauté'),
        ('services-jardinage', 'Jardinage'),
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
    prix           = models.IntegerField(default=0)
    prix_label     = models.CharField(max_length=50, blank=True, help_text="Ex: 15 000 XPF, Gratuit, À débattre")
    prix_unite     = models.CharField(max_length=20, choices=PRIX_UNITE_CHOICES, default='', blank=True)
    categorie      = models.CharField(max_length=50, choices=CATEGORIES)
    sous_categorie = models.CharField(max_length=50, blank=True, default='')
    localisation   = models.CharField(max_length=100, default='Papeete')
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
    verified       = models.BooleanField(default=False)
    views          = models.PositiveIntegerField(default=0)  # impressions (vu a l'ecran)
    clics          = models.PositiveIntegerField(default=0)  # clics (ouverture detail)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Annonce'
        verbose_name_plural = 'Annonces'
        ordering = ['-boost', '-created_at']

    def __str__(self):
        return self.titre

    def get_prix_display_label(self):
        if self.prix_label:
            return self.prix_label
        if self.prix_unite == 'negocier':
            return 'À négocier'
        if self.prix == 0:
            return 'Gratuit'
        base = f"{self.prix:,} XPF".replace(',', '\u00a0')
        if self.prix_unite:
            unite_map = dict(PRIX_UNITE_CHOICES)
            return f"{base} {unite_map.get(self.prix_unite, '')}"
        return base

    def get_main_photo(self):
        return self.photos[0] if self.photos else None

    def increment_views(self):
        """Ancienne methode — maintenant incremente les clics."""
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
