from django.db import models

EMPLACEMENTS = [
    ("billboard", "Billboard plein ecran (25 000 XPF/mois)"),
    ("strip_1",   "Strip 1 - Apres Promos (8 000 XPF/mois)"),
    ("strip_2",   "Strip 2 - Milieu page (8 000 XPF/mois)"),
    ("strip_3",   "Strip 3 - Fin de page (8 000 XPF/mois)"),
    ("haut",      "Sidebar Haut (10 000 XPF/mois)"),
    ("milieu",    "Sidebar Milieu (7 000 XPF/mois)"),
    ("bas",       "Sidebar Bas (5 000 XPF/mois)"),
]

PRIX_PAR_EMPLACEMENT = {
    "billboard": 25000,
    "strip_1":    8000,
    "strip_2":    8000,
    "strip_3":    8000,
    "haut":      10000,
    "milieu":     7000,
    "bas":        5000,
}


class Publicite(models.Model):
    titre        = models.CharField(max_length=200)
    description  = models.CharField(max_length=300, blank=True)
    image        = models.ImageField(upload_to='pubs/', blank=True, null=True)
    image_url    = models.URLField(blank=True, help_text="URL externe si pas d'upload")
    lien         = models.URLField(blank=True)
    emplacement  = models.CharField(max_length=20, choices=EMPLACEMENTS)
    prix         = models.IntegerField(default=0)
    actif        = models.BooleanField(default=True)
    client_nom   = models.CharField(max_length=150, blank=True)
    client_email = models.EmailField(blank=True)
    client_tel   = models.CharField(max_length=20, blank=True)
    date_debut   = models.DateField(null=True, blank=True)
    date_fin     = models.DateField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Publicité'
        verbose_name_plural = 'Publicités'
        ordering = ['emplacement', '-actif']

    def __str__(self):
        return f"{self.titre} ({self.get_emplacement_display()})"

    def save(self, *args, **kwargs):
        if not self.prix:
            self.prix = PRIX_PAR_EMPLACEMENT.get(self.emplacement, 0)
        super().save(*args, **kwargs)

    def get_image(self):
        if self.image:
            return self.image.url
        return self.image_url or None


class DemandePublicite(models.Model):
    nom                  = models.CharField(max_length=150)
    email                = models.EmailField()
    tel                  = models.CharField(max_length=20, blank=True)
    entreprise           = models.CharField(max_length=200, blank=True)
    emplacement_souhaite = models.CharField(max_length=20, choices=EMPLACEMENTS)
    message              = models.TextField(blank=True)
    traite               = models.BooleanField(default=False)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Demande de pub'
        verbose_name_plural = 'Demandes de pub'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nom} — {self.emplacement_souhaite}"
