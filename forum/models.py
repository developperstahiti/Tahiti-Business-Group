from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
import re

User = get_user_model()


class Categorie(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    createur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='forum_categories')
    date_creation = models.DateTimeField(auto_now_add=True)
    nb_abonnes = models.IntegerField(default=0)
    icone = models.CharField(max_length=10, blank=True, default='💬')

    class Meta:
        ordering = ['-nb_abonnes', 'nom']
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class Sujet(models.Model):
    titre = models.CharField(max_length=300)
    slug = models.SlugField(max_length=350, blank=True)
    contenu = models.TextField()
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_sujets')
    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE, related_name='sujets')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    nb_vues = models.IntegerField(default=0)
    nb_votes = models.IntegerField(default=0)
    est_epingle = models.BooleanField(default=False)
    est_ferme = models.BooleanField(default=False)
    photo1 = models.ImageField(upload_to='forum/photos/', blank=True, null=True)
    photo2 = models.ImageField(upload_to='forum/photos/', blank=True, null=True)
    photo3 = models.ImageField(upload_to='forum/photos/', blank=True, null=True)

    class Meta:
        ordering = ['-est_epingle', '-date_creation']
        verbose_name = 'Sujet'
        verbose_name_plural = 'Sujets'

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.titre)[:300]
            self.slug = f"{base}-{self.pk}" if self.pk else base
        super().save(*args, **kwargs)
        if not self.slug.endswith(f'-{self.pk}'):
            self.slug = f"{slugify(self.titre)[:300]}-{self.pk}"
            Sujet.objects.filter(pk=self.pk).update(slug=self.slug)

    def nb_reponses(self):
        return self.reponses.filter(reponse_parente__isnull=True).count()

    def __str__(self):
        return self.titre


class Reponse(models.Model):
    sujet = models.ForeignKey(Sujet, on_delete=models.CASCADE, related_name='reponses')
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_reponses')
    contenu = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    nb_votes = models.IntegerField(default=0)
    reponse_parente = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='sous_reponses')

    class Meta:
        ordering = ['-nb_votes', 'date_creation']
        verbose_name = 'Réponse'
        verbose_name_plural = 'Réponses'

    def __str__(self):
        return f"Réponse de {self.auteur} sur {self.sujet}"


class Vote(models.Model):
    TYPE_CHOICES = [('sujet', 'Sujet'), ('reponse', 'Réponse')]
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_votes')
    type_objet = models.CharField(max_length=10, choices=TYPE_CHOICES)
    objet_id = models.IntegerField()
    valeur = models.IntegerField()  # +1 ou -1

    class Meta:
        unique_together = [('utilisateur', 'type_objet', 'objet_id')]
        verbose_name = 'Vote'

    def __str__(self):
        return f"{self.utilisateur} → {self.type_objet} #{self.objet_id} ({self.valeur:+d})"


class AbonnementCategorie(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_abonnements')
    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE, related_name='abonnes')
    date_abonnement = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('utilisateur', 'categorie')]
        verbose_name = 'Abonnement catégorie'

    def __str__(self):
        return f"{self.utilisateur} → {self.categorie}"
