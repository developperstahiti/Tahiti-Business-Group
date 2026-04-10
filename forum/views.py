import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import F, Q
from django.utils.text import slugify
from django.contrib import messages
from .models import Categorie, Sujet, Reponse, Vote, AbonnementCategorie

logger = logging.getLogger(__name__)


def forum_index(request):
    """Page d'accueil du forum — sujets récents/populaires + catégories."""
    tri = request.GET.get('tri', 'recents')
    sujets = Sujet.objects.select_related('auteur', 'categorie').prefetch_related('reponses')
    if tri == 'populaires':
        sujets = sujets.order_by('-nb_votes', '-date_creation')
    elif tri == 'sans_reponse':
        sujets = sujets.filter(reponses__isnull=True).order_by('-date_creation')
    else:
        sujets = sujets.order_by('-est_epingle', '-date_creation')
    sujets = sujets[:30]
    categories = Categorie.objects.order_by('-nb_abonnes')[:8]
    return render(request, 'forum/index.html', {
        'sujets': sujets, 'categories': categories, 'tri': tri,
    })


def liste_categories(request):
    """Liste toutes les catégories triées par abonnés."""
    categories = Categorie.objects.order_by('-nb_abonnes', 'nom')
    return render(request, 'forum/categories.html', {'categories': categories})


@login_required
def creer_categorie(request):
    """Formulaire création catégorie."""
    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        description = request.POST.get('description', '').strip()
        icone = request.POST.get('icone', '💬').strip() or '💬'
        if not nom:
            messages.error(request, "Le nom est obligatoire.")
        elif Categorie.objects.filter(nom__iexact=nom).exists():
            messages.error(request, "Une catégorie avec ce nom existe déjà.")
        else:
            cat = Categorie.objects.create(
                nom=nom, description=description, icone=icone,
                createur=request.user,
            )
            messages.success(request, f"Catégorie « {cat.nom} » créée !")
            return redirect('forum_categorie', slug=cat.slug)
    return render(request, 'forum/creer_categorie.html')


def detail_categorie(request, slug):
    """Page d'une catégorie avec ses sujets."""
    categorie = get_object_or_404(Categorie, slug=slug)
    tri = request.GET.get('tri', 'recents')
    sujets = Sujet.objects.filter(categorie=categorie).select_related('auteur').prefetch_related('reponses')
    if tri == 'populaires':
        sujets = sujets.order_by('-nb_votes', '-date_creation')
    elif tri == 'sans_reponse':
        sujets = sujets.filter(reponses__isnull=True).order_by('-date_creation')
    else:
        sujets = sujets.order_by('-est_epingle', '-date_creation')

    est_abonne = (
        request.user.is_authenticated and
        AbonnementCategorie.objects.filter(utilisateur=request.user, categorie=categorie).exists()
    )
    return render(request, 'forum/categorie.html', {
        'categorie': categorie, 'sujets': sujets, 'tri': tri, 'est_abonne': est_abonne,
    })


@login_required
def creer_sujet(request):
    """Formulaire création sujet."""
    categories = Categorie.objects.order_by('nom')
    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        contenu = request.POST.get('contenu', '').strip()
        cat_id = request.POST.get('categorie')
        if not titre or not contenu or not cat_id:
            messages.error(request, "Titre, contenu et catégorie sont obligatoires.")
        else:
            try:
                categorie = Categorie.objects.get(pk=cat_id)
            except Categorie.DoesNotExist:
                messages.error(request, "Catégorie invalide.")
                return render(request, 'forum/creer_sujet.html', {'categories': categories})

            sujet = Sujet(titre=titre, contenu=contenu, auteur=request.user, categorie=categorie)
            sujet.save()

            # Photos (max 3)
            for i, field in enumerate(['photo1', 'photo2', 'photo3'], 1):
                f = request.FILES.get(f'photo{i}')
                if f:
                    try:
                        from ads.image_utils import save_webp
                        url = save_webp(f, 'forum', f'sujet_{sujet.pk}_p{i}')
                        setattr(sujet, field, url)
                    except Exception as e:
                        logger.warning("Erreur photo forum: %s", e)
            sujet.save()

            messages.success(request, "Sujet publié !")
            return redirect('forum_sujet', slug=sujet.slug)
    return render(request, 'forum/creer_sujet.html', {'categories': categories})


def detail_sujet(request, slug):
    """Page détail d'un sujet avec ses réponses."""
    sujet = get_object_or_404(Sujet, slug=slug)
    Sujet.objects.filter(pk=sujet.pk).update(nb_vues=F('nb_vues') + 1)

    tri = request.GET.get('tri', 'meilleures')
    reponses_qs = Reponse.objects.filter(
        sujet=sujet, reponse_parente__isnull=True
    ).select_related('auteur').prefetch_related('sous_reponses__auteur')

    if tri == 'recentes':
        reponses_qs = reponses_qs.order_by('date_creation')
    else:
        reponses_qs = reponses_qs.order_by('-nb_votes', 'date_creation')

    # Votes de l'utilisateur connecté
    votes_utilisateur = {}
    if request.user.is_authenticated:
        ids_sujets = [sujet.pk]
        ids_reponses = list(reponses_qs.values_list('pk', flat=True))
        for v in Vote.objects.filter(
            utilisateur=request.user,
            type_objet__in=['sujet', 'reponse'],
        ).filter(
            Q(type_objet='sujet', objet_id__in=ids_sujets) |
            Q(type_objet='reponse', objet_id__in=ids_reponses)
        ):
            votes_utilisateur[f"{v.type_objet}_{v.objet_id}"] = v.valeur

    # Formulaire réponse
    if request.method == 'POST' and request.user.is_authenticated and not sujet.est_ferme:
        contenu = request.POST.get('contenu', '').strip()
        parent_id = request.POST.get('parent_id')
        if contenu:
            parent = None
            if parent_id:
                try:
                    parent = Reponse.objects.get(pk=parent_id, sujet=sujet, reponse_parente__isnull=True)
                except Reponse.DoesNotExist:
                    pass
            Reponse.objects.create(
                sujet=sujet, auteur=request.user, contenu=contenu, reponse_parente=parent,
            )
            messages.success(request, "Réponse publiée !")
            return redirect('forum_sujet', slug=sujet.slug)

    return render(request, 'forum/sujet_detail.html', {
        'sujet': sujet,
        'reponses': list(reponses_qs),
        'tri': tri,
        'votes_utilisateur_json': json.dumps(votes_utilisateur),
    })


@login_required
def mes_sujets(request):
    """Sujets créés par l'utilisateur connecté."""
    sujets = Sujet.objects.filter(auteur=request.user).select_related('categorie').order_by('-date_creation')
    return render(request, 'forum/mes_sujets.html', {'sujets': sujets})


@login_required
@require_POST
def moderer_sujet(request, slug):
    """Épingler/désépingler ou fermer/ouvrir un sujet — staff uniquement."""
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    sujet = get_object_or_404(Sujet, slug=slug)
    action = request.POST.get('action')
    if action == 'epingle':
        sujet.est_epingle = not sujet.est_epingle
        sujet.save(update_fields=['est_epingle'])
    elif action == 'fermer':
        sujet.est_ferme = not sujet.est_ferme
        sujet.save(update_fields=['est_ferme'])
    return redirect('forum_sujet', slug=slug)


@login_required
@require_POST
def forum_vote(request):
    """Vote AJAX +1 / -1 sur sujet ou réponse."""
    type_objet = request.POST.get('type_objet')
    objet_id = request.POST.get('objet_id')
    valeur = request.POST.get('valeur')

    if type_objet not in ('sujet', 'reponse') or valeur not in ('1', '-1'):
        return JsonResponse({'ok': False, 'error': 'Paramètres invalides'}, status=400)

    try:
        objet_id = int(objet_id)
        valeur = int(valeur)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'ID invalide'}, status=400)

    # Récupère le modèle cible
    if type_objet == 'sujet':
        try:
            obj = Sujet.objects.get(pk=objet_id)
        except Sujet.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Sujet introuvable'}, status=404)
    else:
        try:
            obj = Reponse.objects.get(pk=objet_id)
        except Reponse.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Réponse introuvable'}, status=404)

    vote_qs = Vote.objects.filter(utilisateur=request.user, type_objet=type_objet, objet_id=objet_id)
    vote_existant = vote_qs.first()

    if vote_existant:
        if vote_existant.valeur == valeur:
            # Annuler le vote
            delta = -valeur
            vote_qs.delete()
            nouveau_vote = 0
        else:
            # Changer le vote
            delta = valeur - vote_existant.valeur
            vote_existant.valeur = valeur
            vote_existant.save()
            nouveau_vote = valeur
    else:
        # Nouveau vote
        Vote.objects.create(utilisateur=request.user, type_objet=type_objet, objet_id=objet_id, valeur=valeur)
        delta = valeur
        nouveau_vote = valeur

    # Mise à jour atomique du score
    if type_objet == 'sujet':
        Sujet.objects.filter(pk=objet_id).update(nb_votes=F('nb_votes') + delta)
        nouveau_score = Sujet.objects.get(pk=objet_id).nb_votes
    else:
        Reponse.objects.filter(pk=objet_id).update(nb_votes=F('nb_votes') + delta)
        nouveau_score = Reponse.objects.get(pk=objet_id).nb_votes

    return JsonResponse({'ok': True, 'score': nouveau_score, 'vote': nouveau_vote})


@login_required
@require_POST
def toggle_abonnement(request, slug):
    """S'abonner / se désabonner d'une catégorie."""
    categorie = get_object_or_404(Categorie, slug=slug)
    ab, created = AbonnementCategorie.objects.get_or_create(
        utilisateur=request.user, categorie=categorie,
    )
    if not created:
        ab.delete()
        Categorie.objects.filter(pk=categorie.pk).update(nb_abonnes=F('nb_abonnes') - 1)
        est_abonne = False
    else:
        Categorie.objects.filter(pk=categorie.pk).update(nb_abonnes=F('nb_abonnes') + 1)
        est_abonne = True

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        nb = Categorie.objects.get(pk=categorie.pk).nb_abonnes
        return JsonResponse({'ok': True, 'est_abonne': est_abonne, 'nb_abonnes': nb})
    return redirect('forum_categorie', slug=slug)
