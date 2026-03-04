from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Publicite, DemandePublicite
from .forms import PubliciteForm, DemandePubliciteForm


def _staff_required(request):
    """Retourne True si l'accès est autorisé, sinon redirige."""
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "Accès réservé aux administrateurs.")
        return False
    return True


@login_required
def pub_creer(request):
    if not _staff_required(request):
        return redirect('index')
    emplacement = request.GET.get('emplacement', '')
    initial = {'emplacement': emplacement} if emplacement else {}
    form = PubliciteForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Publicité créée avec succès.")
        return redirect('admin_dashboard')
    return render(request, 'pubs/pub_form.html', {'form': form, 'action': 'Créer'})


@login_required
def pub_modifier(request, pk):
    if not _staff_required(request):
        return redirect('index')
    pub = get_object_or_404(Publicite, pk=pk)
    form = PubliciteForm(request.POST or None, request.FILES or None, instance=pub)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Publicité modifiée avec succès.")
        return redirect('admin_dashboard')
    return render(request, 'pubs/pub_form.html', {'form': form, 'pub': pub, 'action': 'Modifier'})


@login_required
def pub_supprimer(request, pk):
    if not _staff_required(request):
        return redirect('index')
    pub = get_object_or_404(Publicite, pk=pk)
    if request.method == 'POST':
        # Libérer le slot : effacer le contenu client sans supprimer l'objet
        # → l'emplacement redevient "disponible" et affiche l'encart vide
        if pub.image:
            pub.image.delete(save=False)
        pub.titre       = 'Emplacement disponible'
        pub.description = ''
        pub.image_url   = ''
        pub.lien        = ''
        pub.actif       = False
        pub.client_nom  = ''
        pub.client_email = ''
        pub.client_tel  = ''
        pub.date_debut  = None
        pub.date_fin    = None
        pub.save()
        messages.success(request, "Slot libéré — l'emplacement est à nouveau disponible à la réservation.")
    return redirect('admin_dashboard')


@login_required
def pub_toggle(request, pk):
    if not _staff_required(request):
        return redirect('index')
    pub = get_object_or_404(Publicite, pk=pk)
    if request.method == 'POST':
        pub.actif = not pub.actif
        pub.save()
    return redirect('admin_dashboard')


def tarifs_pubs(request):
    pubs_haut = Publicite.objects.filter(emplacement='haut', actif=True).first()
    pubs_milieu = Publicite.objects.filter(emplacement='milieu', actif=True).first()
    pubs_bas = Publicite.objects.filter(emplacement='bas', actif=True).first()

    return render(request, 'pubs/tarifs.html', {
        'pubs_haut': pubs_haut,
        'pubs_milieu': pubs_milieu,
        'pubs_bas': pubs_bas,
        'tarifs': [
            {'emplacement': 'Haut de sidebar', 'prix': 60000, 'desc': 'Meilleure visibilité, premier regard'},
            {'emplacement': 'Milieu de sidebar', 'prix': 40000, 'desc': 'Position centrale, très efficace'},
            {'emplacement': 'Bas de sidebar', 'prix': 20000, 'desc': 'Présence permanente, tarif abordable'},
        ],
    })


def demande_pub(request):
    form = DemandePubliciteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Votre demande a été envoyée ! Nous vous contacterons sous 24h.")
        return redirect('tarifs_pubs')

    return render(request, 'pubs/demande.html', {'form': form})