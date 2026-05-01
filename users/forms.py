from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'votre@email.com', 'class': 'form-input'}),
        label='Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••', 'class': 'form-input'}),
        label='Mot de passe'
    )


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••', 'class': 'form-input'}),
        label='Mot de passe',
        min_length=8
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••', 'class': 'form-input'}),
        label='Confirmer le mot de passe'
    )

    # Only allow personnel and pro — admin is reserved for superuser creation
    ALLOWED_ROLES = [
        ('personnel', 'Particulier'),
        ('pro', 'Professionnel'),
    ]
    role = forms.ChoiceField(
        choices=ALLOWED_ROLES,
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='Type de compte',
    )

    nom_entreprise = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': "Nom de votre entreprise", 'class': 'form-input'}),
        label="Nom d'entreprise",
    )

    numero_tahiti = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': "Ex : N°A12345", 'class': 'form-input'}),
        label="Numéro Tahiti (ISPF)",
    )

    # Code de parrainage (caché, transmis via ?ref=CODE)
    ref = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = User
        fields = ['email', 'nom', 'tel', 'role', 'nom_entreprise', 'numero_tahiti']
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'votre@email.com', 'class': 'form-input'}),
            'nom': forms.TextInput(attrs={'placeholder': 'Votre nom complet', 'class': 'form-input'}),
            'tel': forms.TextInput(attrs={'placeholder': '89 XX XX XX', 'class': 'form-input'}),
        }
        labels = {
            'email': 'Email *',
            'nom': 'Nom complet',
            'tel': 'Téléphone',
        }

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role not in ('personnel', 'pro'):
            raise forms.ValidationError("Type de compte invalide.")
        return role

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        if password != cleaned_data.get('password2'):
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        # Valider le mot de passe avec AUTH_PASSWORD_VALIDATORS
        if password:
            # Build a temporary user instance for UserAttributeSimilarityValidator
            temp_user = User(
                email=cleaned_data.get('email', ''),
                nom=cleaned_data.get('nom', ''),
            )
            try:
                validate_password(password, user=temp_user)
            except forms.ValidationError as e:
                self.add_error('password', e)
        if cleaned_data.get('role') == 'pro' and not cleaned_data.get('nom_entreprise', '').strip():
            self.add_error('nom_entreprise', "Le nom d'entreprise est obligatoire pour un compte Pro.")
        if cleaned_data.get('role') == 'pro' and not cleaned_data.get('numero_tahiti', '').strip():
            self.add_error('numero_tahiti', "Le numéro Tahiti est obligatoire pour un compte Pro.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        # Lier au parrain si le code est valide
        ref = (self.cleaned_data.get('ref') or '').strip().upper()
        if ref:
            parrain = User.objects.filter(referral_code=ref).first()
            if parrain:
                user.referred_by = parrain
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['nom', 'tel', 'avatar', 'bio']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-input'}),
            'tel': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '89 XX XX XX'}),
            'bio': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'maxlength': 500,
                'placeholder': 'Presentez-vous en quelques mots (visible sur votre profil public)',
            }),
        }
        labels = {
            'bio': 'Bio (visible sur votre profil)',
        }