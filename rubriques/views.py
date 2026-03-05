from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from .models import ArticlePromo, ArticleInfo, ArticleNouveaute


def rubriques_index(request):
    promos     = ArticlePromo.objects.filter(statut='valide').select_related('pro_user')[:4]
    infos      = ArticleInfo.objects.filter(statut='valide').select_related('auteur')[:4]
    nouveautes = ArticleNouveaute.objects.filter(statut='valide').select_related('pro_user')[:4]
    return render(request, 'rubriques/index.html', {
        'promos':     promos,
        'infos':      infos,
        'nouveautes': nouveautes,
    })


@login_required
def deposer_promo(request):
    if not request.user.is_pro:
        messages.error(request, "Accès réservé aux comptes professionnels.")
        return redirect('rubriques_index')
    if not request.user.abonnement_promo_actif:
        messages.error(request, "Un abonnement actif est requis pour publier une promo. Contactez TBG pour activer votre accès.")
        return redirect('rubriques_index')
    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        contenu = request.POST.get('contenu', '').strip()
        lien  = request.POST.get('lien_promo', '').strip()
        if titre and contenu:
            ArticlePromo.objects.create(
                pro_user=request.user,
                titre=titre,
                contenu=contenu,
                lien_promo=lien,
            )
            messages.success(request, "Votre promo est en attente de validation par l'équipe TBG.")
            return redirect('rubriques_index')
    return render(request, 'rubriques/deposer_promo.html')


@login_required
def deposer_info(request):
    if request.method == 'POST':
        titre  = request.POST.get('titre', '').strip()
        contenu = request.POST.get('contenu', '').strip()
        source = request.POST.get('source_media', '').strip()
        if titre and contenu:
            ArticleInfo.objects.create(
                auteur=request.user,
                titre=titre,
                contenu=contenu,
                source_media=source,
            )
            messages.success(request, "Votre info est en attente de validation par l'équipe TBG.")
            return redirect('rubriques_index')
    return render(request, 'rubriques/deposer_info.html')


@login_required
def deposer_nouveaute(request):
    if not request.user.is_pro:
        messages.error(request, "Accès réservé aux comptes professionnels.")
        return redirect('rubriques_index')
    if request.method == 'POST':
        titre  = request.POST.get('titre', '').strip()
        contenu = request.POST.get('contenu', '').strip()
        lien   = request.POST.get('lien_redirection', '').strip()
        if titre and contenu:
            ArticleNouveaute.objects.create(
                pro_user=request.user,
                titre=titre,
                contenu=contenu,
                lien_redirection=lien,
            )
            messages.success(request, "Votre nouveauté est en attente de validation par l'équipe TBG.")
            return redirect('rubriques_index')
    return render(request, 'rubriques/deposer_nouveaute.html')


def promo_detail(request, pk):
    article = get_object_or_404(ArticlePromo, pk=pk, statut='valide')
    return render(request, 'rubriques/detail.html', {
        'article': article,
        'type': 'promo',
        'emoji': '💰',
        'badge': 'Promo',
        'lien': article.lien_promo,
        'lien_label': "Voir l'offre",
        'auteur': article.pro_user,
    })


def info_detail(request, pk):
    article = get_object_or_404(ArticleInfo, pk=pk, statut='valide')
    return render(request, 'rubriques/detail.html', {
        'article': article,
        'type': 'info',
        'emoji': '📰',
        'badge': 'Info',
        'lien': article.source_media,
        'lien_label': 'Lire la source',
        'auteur': article.auteur,
    })


def nouveaute_detail(request, pk):
    article = get_object_or_404(ArticleNouveaute, pk=pk, statut='valide')
    return render(request, 'rubriques/detail.html', {
        'article': article,
        'type': 'nouveaute',
        'emoji': '🚀',
        'badge': 'Nouveauté',
        'lien': article.lien_redirection,
        'lien_label': 'En savoir plus',
        'auteur': article.pro_user,
    })


@login_required
def moderation_dashboard(request):
    if not request.user.is_staff:
        raise Http404
    promos_attente     = ArticlePromo.objects.filter(statut='en_attente').select_related('pro_user')
    infos_attente      = ArticleInfo.objects.filter(statut='en_attente').select_related('auteur')
    nouveautes_attente = ArticleNouveaute.objects.filter(statut='en_attente').select_related('pro_user')
    promos_recents     = ArticlePromo.objects.exclude(statut='en_attente').select_related('pro_user')[:5]
    infos_recents      = ArticleInfo.objects.exclude(statut='en_attente').select_related('auteur')[:5]
    nouveautes_recents = ArticleNouveaute.objects.exclude(statut='en_attente').select_related('pro_user')[:5]
    return render(request, 'rubriques/moderation.html', {
        'promos_attente':     promos_attente,
        'infos_attente':      infos_attente,
        'nouveautes_attente': nouveautes_attente,
        'promos_recents':     promos_recents,
        'infos_recents':      infos_recents,
        'nouveautes_recents': nouveautes_recents,
        'total_attente':      promos_attente.count() + infos_attente.count() + nouveautes_attente.count(),
    })


@login_required
def moderer_article(request, type_article, pk, action):
    if not request.user.is_staff:
        raise Http404
    MODEL_MAP = {
        'promo':     ArticlePromo,
        'info':      ArticleInfo,
        'nouveaute': ArticleNouveaute,
    }
    Model = MODEL_MAP.get(type_article)
    if not Model or action not in ('valider', 'refuser'):
        raise Http404
    article = get_object_or_404(Model, pk=pk)
    article.statut = 'valide' if action == 'valider' else 'refuse'
    article.save()
    verb = 'validé' if action == 'valider' else 'refusé'
    messages.success(request, f'Article « {article.titre} » {verb}.')
    return redirect('moderation_dashboard')