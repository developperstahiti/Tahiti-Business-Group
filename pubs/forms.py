from django import forms
from .models import Publicite, DemandePublicite, EMPLACEMENTS, DUREE_CHOICES


class PubliciteForm(forms.ModelForm):
    class Meta:
        model = Publicite
        fields = [
            'titre', 'description', 'image', 'image_url',
            'video', 'video_url', 'lien',
            'emplacement', 'actif',
            'client_nom', 'client_email', 'client_tel',
            'date_debut', 'date_fin',
        ]
        widgets = {
            'titre':        forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom de la publicité'}),
            'description':  forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Description courte (optionnel)'}),
            'image_url':    forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'video_url':    forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...mp4'}),
            'lien':         forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'emplacement':  forms.Select(attrs={'class': 'form-input'}),
            'client_nom':   forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom du client'}),
            'client_email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'client@email.com'}),
            'client_tel':   forms.TextInput(attrs={'class': 'form-input', 'placeholder': '89 XX XX XX'}),
            'date_debut':   forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'date_fin':     forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }


class DemandePubliciteForm(forms.ModelForm):
    class Meta:
        model = DemandePublicite
        fields = ['nom', 'email', 'tel', 'entreprise', 'emplacement_souhaite', 'message']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Votre nom'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'votre@email.com'}),
            'tel': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '89 XX XX XX'}),
            'entreprise': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom de votre entreprise'}),
            'emplacement_souhaite': forms.Select(attrs={'class': 'form-input'}),
            'message': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 4,
                'placeholder': 'Décrivez votre besoin...'
            }),
        }


class DepotPubliciteForm(forms.Form):
    """Formulaire self-service pour déposer et payer une publicité."""
    titre = forms.CharField(
        max_length=200, label='Titre de votre pub',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Promo -30% chez MonShop'}),
    )
    image = forms.ImageField(
        label='Image publicitaire',
        required=False,
        help_text='JPG, PNG ou WebP. Sera redimensionnée automatiquement.',
    )
    image_url = forms.URLField(
        label="Lien de l'image",
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://exemple.com/mon-image.jpg'}),
    )
    video = forms.FileField(
        label='Vidéo publicitaire',
        required=False,
        help_text='MP4, WebM ou MOV. Max 50 Mo.',
        widget=forms.ClearableFileInput(attrs={'accept': 'video/*'}),
    )
    video_url = forms.URLField(
        label="Lien de la vidéo",
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://exemple.com/ma-video.mp4'}),
    )
    lien = forms.URLField(
        label='Lien de destination',
        widget=forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://votre-site.com'}),
    )
    emplacement = forms.ChoiceField(
        choices=EMPLACEMENTS, label='Emplacement',
        widget=forms.Select(attrs={'class': 'form-input', 'id': 'id_emplacement'}),
    )
    duree = forms.ChoiceField(
        choices=DUREE_CHOICES, label='Durée',
        widget=forms.Select(attrs={'class': 'form-input', 'id': 'id_duree'}),
    )
    client_nom = forms.CharField(
        max_length=150, label='Votre nom / entreprise',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom ou raison sociale'}),
    )
    client_email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'contact@entreprise.pf'}),
    )
    client_tel = forms.CharField(
        max_length=20, label='Téléphone', required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '89 XX XX XX'}),
    )