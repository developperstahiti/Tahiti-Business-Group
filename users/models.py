import random
import string

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


def _generate_referral_code(length=8):
    """Generate a random uppercase alphanumeric referral code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('personnel', 'Particulier'),
        ('pro', 'Professionnel'),
        ('admin', 'Administrateur'),
    ]

    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=150, blank=True)
    tel = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='personnel')
    nom_entreprise = models.CharField(max_length=150, blank=True, default='', help_text="Obligatoire pour les comptes Pro")
    numero_tahiti = models.CharField(max_length=50, blank=True, default='', help_text="Numéro Tahiti ISPF (obligatoire pour les pros)")
    abonnement_promo_actif = models.BooleanField(default=False, help_text="Accès payant à la section Promos")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    avatar_url = models.URLField(max_length=500, blank=True, default='')
    email_verified = models.BooleanField(default=True)  # True pour les comptes existants
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_imported = models.BooleanField(default=False, db_index=True,
                                      help_text="Compte créé automatiquement depuis l'import petites-annonces.pf")

    # Parrainage
    referral_code = models.CharField(max_length=20, blank=True, default='', unique=True, db_index=True,
                                     help_text="Code unique de parrainage (auto-généré)")
    referred_by = models.ForeignKey('self', null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='referrals',
                                    help_text="Qui a parrainé ce user")
    referral_rewards_earned = models.PositiveIntegerField(default=0,
                                    help_text="Nb de récompenses (boosts gratuits) gagnées")

    # Affichage profil enrichi
    bio = models.TextField(max_length=500, blank=True, default='',
                           help_text="Présentation libre du vendeur")

    # Étoiles d'affichage (utilisées en fallback si pas de vraies notes)
    fake_rating = models.FloatField(default=0,
                           help_text="Note d'affichage 3.9-5.0 utilisée si pas de vraies notes")
    fake_review_count = models.PositiveIntegerField(default=0,
                           help_text="Nombre d'avis fictifs (cohérent avec fake_rating)")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return self.nom or self.email

    @property
    def is_pro(self):
        return self.role in ('pro', 'admin')

    @property
    def is_admin_role(self):
        return self.role == 'admin'

    def save(self, *args, **kwargs):
        # Auto-generate a unique referral code on first save if missing
        if not self.referral_code:
            for _ in range(20):
                code = _generate_referral_code()
                if not type(self).objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break
        super().save(*args, **kwargs)


class Profil(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profil',
    )
    photo_profil = models.ImageField(upload_to='profils/photos/', blank=True, null=True)
    photo_profil_url = models.URLField(max_length=500, blank=True, default='')
    image_fond = models.ImageField(upload_to='profils/bannieres/', blank=True, null=True)
    image_fond_url = models.URLField(max_length=500, blank=True, default='')

    bio = models.TextField(max_length=500, blank=True, default='')
    localisation = models.CharField(max_length=100, blank=True, default='')
    whatsapp = models.CharField(max_length=20, blank=True, default='')
    facebook_url = models.URLField(blank=True, default='')
    instagram_url = models.URLField(blank=True, default='')
    site_web = models.URLField(blank=True, default='')

    class Meta:
        verbose_name = 'Profil'
        verbose_name_plural = 'Profils'

    def __str__(self):
        return f"Profil de {self.user}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profil(sender, instance, created, **kwargs):
    """Crée automatiquement un Profil quand un User est créé."""
    if created:
        Profil.objects.create(user=instance)