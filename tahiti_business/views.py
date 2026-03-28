from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django_otp import devices_for_user


@login_required
def otp_verify(request):
    """Page de vérification TOTP pour l'admin."""
    if not request.user.is_staff:
        return redirect('/')

    error = None
    if request.method == 'POST':
        token = request.POST.get('otp_token', '').strip()
        if token:
            for device in devices_for_user(request.user, confirmed=True):
                if device.verify_token(token):
                    request.session['otp_admin_verified'] = True
                    next_url = request.GET.get('next', '/3319cdb9fc7eb59/')
                    if not url_has_allowed_host_and_scheme(
                        url=next_url,
                        allowed_hosts={request.get_host()},
                        require_https=request.is_secure(),
                    ):
                        next_url = '/3319cdb9fc7eb59/'
                    return redirect(next_url)
            error = 'Code OTP invalide. Réessayez.'
        else:
            error = 'Veuillez saisir votre code OTP.'

    return render(request, 'admin/otp_verify.html', {
        'error': error,
        'next': request.GET.get('next', '/3319cdb9fc7eb59/'),
    })
