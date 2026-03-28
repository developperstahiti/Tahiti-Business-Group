from django.contrib.auth.decorators import user_passes_test


def staff_required(view_func):
    """Decorateur qui exige que l'utilisateur soit connecte et staff."""
    decorated = user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url='/users/login/',
    )(view_func)
    return decorated
