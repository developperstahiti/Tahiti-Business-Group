from django import forms
from .models import Publicite, DemandePublicite


class PubliciteForm(forms.ModelForm):
    class Meta:
        model = Publicite
        fields = [
            'titre', 'description', 'image', 'image_url', 'lien',
            'emplacement', 'actif',
            'client_nom', 'client_email', 'client_tel',
            'date_debut', 'date_fin',
        ]
        widgets = {
            'titre':        forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom de la publicité'}),
            'description':  forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Description courte (optionnel)'}),
            'image_url':    forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
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