from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm, RegisterForm, ProfileForm
from ads.models import Annonce, Message


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            messages.success(request, f"Bienvenue {user.nom or user.email} !")
            return redirect(request.GET.get('next', 'index'))
        else:
            form.add_error(None, "Email ou mot de passe incorrect.")

    return render(request, 'users/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Compte créé avec succès ! Bienvenue sur Tahiti Business Group.")
        return redirect('index')

    return render(request, 'users/register.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('index')


@login_required
def mon_compte(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Profil mis à jour avec succès.")
        return redirect('mon_compte')

    annonces = Annonce.objects.filter(user=request.user).order_by('-created_at')
    messages_recus = Message.objects.filter(
        annonce__user=request.user
    ).select_related('annonce').order_by('-created_at')[:10]

    stats = {
        'total': annonces.count(),
        'actives': annonces.filter(statut='actif').count(),
        'vendues': annonces.filter(statut='vendu').count(),
        'vues': sum(a.views for a in annonces),
        'messages': messages_recus.count(),
    }

    return render(request, 'users/mon_compte.html', {
        'form': form,
        'annonces': annonces[:6],
        'messages_recus': messages_recus,
        'stats': stats,
    })


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, "Accès refusé.")
        return redirect('index')

    from pubs.models import Publicite, DemandePublicite
    from .models import User

    SLOTS = [
        {'key': 'billboard', 'label': 'Billboard',     'desc': 'Plein écran en haut de page',       'prix': 25000, 'icon': '🖼'},
        {'key': 'strip_1',   'label': 'Strip 1',       'desc': 'Après la section Promos',            'prix': 8000,  'icon': '▬'},
        {'key': 'strip_2',   'label': 'Strip 2',       'desc': 'Milieu de page (après catégorie 2)', 'prix': 8000,  'icon': '▬'},
        {'key': 'strip_3',   'label': 'Strip 3',       'desc': 'Fin de page (après catégorie 4)',    'prix': 8000,  'icon': '▬'},
        {'key': 'haut',      'label': 'Sidebar Haut',  'desc': 'Sidebar – position haute',           'prix': 10000, 'icon': '◻'},
        {'key': 'milieu',    'label': 'Sidebar Milieu','desc': 'Sidebar – position milieu',          'prix': 7000,  'icon': '◻'},
        {'key': 'bas',       'label': 'Sidebar Bas',   'desc': 'Sidebar – position basse',           'prix': 5000,  'icon': '◻'},
    ]

    # Associer chaque slot à sa pub active
    pubs_par_slot = {}
    for slot in SLOTS:
        pubs_par_slot[slot['key']] = Publicite.objects.filter(emplacement=slot['key']).first()

    slots_with_pub = []
    for slot in SLOTS:
        slots_with_pub.append({**slot, 'pub': pubs_par_slot.get(slot['key'])})

    stats = {
        'annonces_total':   Annonce.objects.count(),
        'annonces_actives': Annonce.objects.filter(statut='actif').count(),
        'annonces_moderees':Annonce.objects.filter(statut='modere').count(),
        'users_total':      User.objects.count(),
        'pubs_actives':     Publicite.objects.filter(actif=True).count(),
        'demandes_pubs':    DemandePublicite.objects.filter(traite=False).count(),
    }

    annonces_recentes = Annonce.objects.select_related('user').order_by('-created_at')[:20]
    demandes_pubs     = DemandePublicite.objects.filter(traite=False).order_by('-created_at')

    return render(request, 'users/admin_dashboard.html', {
        'stats':          stats,
        'slots':          slots_with_pub,
        'annonces_recentes': annonces_recentes,
        'demandes_pubs':  demandes_pubs,
    })


@login_required
def moderer_annonce(request, pk):
    if not request.user.is_staff:
        return redirect('index')
    annonce = Annonce.objects.get(pk=pk)
    action = request.POST.get('action')
    if action == 'approuver':
        annonce.statut = 'actif'
    elif action == 'moderer':
        annonce.statut = 'modere'
    elif action == 'supprimer':
        annonce.delete()
        messages.success(request, "Annonce supprimée.")
        return redirect('admin_dashboard')
    annonce.save()
    messages.success(request, f"Annonce {action}e.")
    return redirect('admin_dashboard')