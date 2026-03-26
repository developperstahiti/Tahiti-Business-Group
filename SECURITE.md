# Double Authentification (2FA) — Admin TBG

## Activer le 2FA sur votre compte admin

1. Connectez-vous sur l'admin : `https://tahitibusinessgroup.com/3319cdb9fc7eb59/`
2. Entrez votre email et mot de passe
3. Vous serez redirige vers la page de configuration 2FA
4. Allez sur : `https://tahitibusinessgroup.com/account/two_factor/setup/`
5. Scannez le QR code avec Google Authenticator ou Authy
6. Entrez le code a 6 chiffres pour confirmer
7. Generez et notez vos codes de recuperation d'urgence

## Connexion avec 2FA

1. Allez sur l'admin
2. Entrez email + mot de passe
3. Entrez le code a 6 chiffres de votre app d'authentification
4. Vous etes connecte

## En cas de perte du telephone

### Si vous avez vos codes de recuperation
1. Sur la page de login admin, apres email + mot de passe
2. Cliquez sur "Utiliser un code de recuperation"
3. Entrez un de vos codes de recuperation (usage unique)
4. Une fois connecte, reconfigurez le 2FA avec votre nouveau telephone

### En cas d'urgence (aucun code de recuperation)
Executez cette commande sur Railway :
```
python manage.py shell -c "
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice
TOTPDevice.objects.filter(user__email='mathyscocogames@gmail.com').delete()
StaticDevice.objects.filter(user__email='mathyscocogames@gmail.com').delete()
print('2FA desactive')
"
```
Puis reconnectez-vous et reconfigurez le 2FA.

## URLs admin (a garder secret)

- Admin Django : `/3319cdb9fc7eb59/`
- Dashboard custom : `/users/c01e87364339aac/`
- Configuration 2FA : `/account/two_factor/setup/`
