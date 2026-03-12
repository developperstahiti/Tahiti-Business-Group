from django import forms
from .models import Annonce, Message, CATEGORIES


class AnnonceForm(forms.ModelForm):
    class Meta:
        model = Annonce
        fields = ['titre', 'categorie', 'prix', 'prix_label', 'localisation', 'description']
        widgets = {
            'titre': forms.TextInput(attrs={
                'placeholder': 'Titre de votre annonce',
                'class': 'form-input'
            }),
            'categorie': forms.Select(attrs={'class': 'form-input'}),
            'prix': forms.NumberInput(attrs={
                'placeholder': '0',
                'class': 'form-input'
            }),
            'prix_label': forms.TextInput(attrs={
                'placeholder': 'Rempli automatiquement',
                'class': 'form-input',
                'readonly': 'readonly',
                'style': 'background-color: #f3f4f6; color: #9ca3af; cursor: not-allowed;',
            }),
            'localisation': forms.TextInput(attrs={
                'placeholder': 'Ex: Papeete, Faa\'a, Moorea...',
                'class': 'form-input'
            }),
            'description': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Décrivez votre article ou service...',
                'class': 'form-input'
            }),
        }
        labels = {
            'titre': 'Titre de l\'annonce *',
            'categorie': 'Catégorie *',
            'prix': 'Prix (XPF)',
            'prix_label': 'Affichage prix',
            'localisation': 'Localisation',
            'description': 'Description *',
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Votre message...',
                'class': 'form-input'
            }),
        }
        labels = {
            'content': 'Message *',
        }