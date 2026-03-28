import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from ads.decorators import staff_required
from django.contrib import messages
from django.http import Http404, JsonResponse
from ads.image_utils import save_webp
from .models import ArticlePromo, ArticleInfo, ArticleNouveaute

logger = logging.getLogger(__name__)

TEMPLATE_DEPOSER = 'rubriques/deposer_article.html'


def _attach_photo(request, article, prefix):
    photo_file = request.FILES.get('photo')
    if photo_file:
        try:
            article.photo = save_webp(photo_file, 'rubriques', f'{prefix}_{article.pk}')
            article.save(update_fields=['photo'])
        except Exception as e:
            logger.error("Erreur sauvegarde photo rubrique: %s", e)


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
    if request.method == 'POST':
        titre   = request.POST.get('titre', '').strip()
        contenu = request.POST.get('contenu', '').strip()
        lien    = request.POST.get('lien', '').strip()
        if titre and contenu:
            article = ArticlePromo.objects.create(
                pro_user=request.user, titre=titre, contenu=contenu, lien_promo=lien,
            )
            _attach_photo(request, article, 'promo')
            messages.success(request, "Votre promotion est en attente de validation par l'équipe TBG.")
            return redirect('rubriques_index')
    return render(request, TEMPLATE_DEPOSER, {
        'emoji':         '💰',
        'titre_page':    'Déposer une promotion',
        'couleur':       'amber',
        'bouton_label':  'Soumettre la promotion',
        'lien_label':    "Lien vers l'offre (optionnel)",
        'lien_placeholder': 'https://votre-site.pf/promo',
        'titre_placeholder': 'Ex : iPhone 15 -20% chez Hi-Fi Store Punaauia',
        'contenu_placeholder': 'Décrivez la promotion : article(s) concerné(s), réduction, durée, conditions...',
        'regles': "Réductions réelles uniquement. Toute actualité sans prix sera redirigée vers la rubrique Infos média.",
    })


@login_required
def deposer_info(request):
    if request.method == 'POST':
        titre   = request.POST.get('titre', '').strip()
        contenu = request.POST.get('contenu', '').strip()
        lien    = request.POST.get('lien', '').strip()
        if titre and contenu:
            article = ArticleInfo.objects.create(
                auteur=request.user, titre=titre, contenu=contenu, source_media=lien,
            )
            _attach_photo(request, article, 'info')
            messages.success(request, "Votre info est en attente de validation par l'équipe TBG.")
            return redirect('rubriques_index')
    return render(request, TEMPLATE_DEPOSER, {
        'emoji':         '📰',
        'titre_page':    'Soumettre une actualité',
        'couleur':       'blue',
        'bouton_label':  "Soumettre l'info",
        'lien_label':    'Lien source (optionnel mais recommandé)',
        'lien_placeholder': 'https://www.tahiti-infos.com/...',
        'titre_placeholder': 'Ex : Rappel Toyota — défaut sur les freins ABS',
        'contenu_placeholder': 'Résumez l\'actualité en 2-4 phrases...',
        'regles': "Actualités factuelles uniquement. Aucun prix, aucune pub déguisée. Si votre article contient des prix/réductions → utilisez la rubrique Promotion.",
    })


@login_required
def deposer_nouveaute(request):
    if not request.user.is_pro:
        messages.error(request, "Accès réservé aux comptes professionnels.")
        return redirect('rubriques_index')
    if request.method == 'POST':
        titre   = request.POST.get('titre', '').strip()
        contenu = request.POST.get('contenu', '').strip()
        lien    = request.POST.get('lien', '').strip()
        if titre and contenu:
            article = ArticleNouveaute.objects.create(
                pro_user=request.user, titre=titre, contenu=contenu, lien_redirection=lien,
            )
            _attach_photo(request, article, 'nouv')
            messages.success(request, "Votre nouveauté est en attente de validation par l'équipe TBG.")
            return redirect('rubriques_index')
    return render(request, TEMPLATE_DEPOSER, {
        'emoji':         '🚀',
        'titre_page':    'Publier une nouveauté / À tester absolument',
        'couleur':       'emerald',
        'bouton_label':  'Publier la nouveauté',
        'lien_label':    'Lien de redirection (optionnel)',
        'lien_placeholder': 'https://votre-site.pf ou page Instagram',
        'titre_placeholder': 'Ex : Nouveau restaurant Poke Tahiti à Mahina — ouverture vendredi',
        'contenu_placeholder': 'Décrivez votre nouveauté : lieu, service, horaires, contact...',
        'regles': "Nouveautés commerciales réelles uniquement. Si votre publication contient une réduction → utilisez la rubrique Promotion.",
    })


def promo_detail(request, pk):
    article = get_object_or_404(ArticlePromo, pk=pk, statut='valide')
    return render(request, 'rubriques/detail.html', {
        'article': article, 'emoji': '💰', 'badge': 'Promotion',
        'lien': article.lien_promo, 'lien_label': "Voir l'offre",
        'auteur': article.pro_user,
    })


def info_detail(request, pk):
    article = get_object_or_404(ArticleInfo, pk=pk, statut='valide')
    return render(request, 'rubriques/detail.html', {
        'article': article, 'emoji': '📰', 'badge': 'Infos média',
        'lien': article.source_media, 'lien_label': 'Lire la source',
        'auteur': article.auteur,
    })


def nouveaute_detail(request, pk):
    article = get_object_or_404(ArticleNouveaute, pk=pk, statut='valide')
    return render(request, 'rubriques/detail.html', {
        'article': article, 'emoji': '🚀', 'badge': 'Nouveautés',
        'lien': article.lien_redirection, 'lien_label': 'En savoir plus',
        'auteur': article.pro_user,
    })


@staff_required
def moderation_dashboard(request):
    promos_attente     = ArticlePromo.objects.filter(statut='en_attente').select_related('pro_user')
    infos_attente      = ArticleInfo.objects.filter(statut='en_attente').select_related('auteur')
    nouveautes_attente = ArticleNouveaute.objects.filter(statut='en_attente').select_related('pro_user')
    return render(request, 'rubriques/moderation.html', {
        'promos_attente':     promos_attente,
        'infos_attente':      infos_attente,
        'nouveautes_attente': nouveautes_attente,
        'promos_recents':     ArticlePromo.objects.exclude(statut='en_attente').select_related('pro_user')[:5],
        'infos_recents':      ArticleInfo.objects.exclude(statut='en_attente').select_related('auteur')[:5],
        'nouveautes_recents': ArticleNouveaute.objects.exclude(statut='en_attente').select_related('pro_user')[:5],
        'total_attente':      promos_attente.count() + infos_attente.count() + nouveautes_attente.count(),
    })


@staff_required
def run_agents_view(request):
    """Lance les agents de scraping en arriere-plan — admin only."""
    import threading
    from .agents import run_all_agents

    def _run():
        try:
            import django
            django.db.connections.close_all()
            run_all_agents()
        except Exception:
            import logging
            logging.getLogger('rubriques.agents').exception("Erreur agent background")

    threading.Thread(target=_run, daemon=True).start()
    messages.success(request, "Agents lances en arriere-plan. Rafraichissez la page dans ~30 secondes pour voir les nouveaux articles.")
    return redirect('rubriques_index')


@staff_required
def moderer_article(request, type_article, pk, action):
    MODEL_MAP = {'promo': ArticlePromo, 'info': ArticleInfo, 'nouveaute': ArticleNouveaute}
    Model = MODEL_MAP.get(type_article)
    if not Model or action not in ('valider', 'refuser'):
        raise Http404
    article = get_object_or_404(Model, pk=pk)
    article.statut = 'valide' if action == 'valider' else 'refuse'
    article.save()
    messages.success(request, f'Article « {article.titre} » {"validé" if action == "valider" else "refusé"}.')
    return redirect('moderation_dashboard')
