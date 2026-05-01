from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('annonces/', views.liste_annonces, name='liste_annonces'),
    # Specific action paths MUST come before the generic <slug> pattern
    path('annonces/<int:pk>/edit/', views.edit_annonce, name='edit_annonce'),
    path('annonces/<int:pk>/supprimer/', views.supprimer_annonce, name='supprimer_annonce'),
    path('annonces/<int:pk>/vendu/', views.marquer_vendu, name='marquer_vendu'),
    path('annonces/<int:pk>/contact/', views.contact_annonce, name='contact_annonce'),
    path('annonces/<int:pk>/signaler/', views.signaler_annonce, name='signaler_annonce'),
    # Generic detail patterns after all specific ones
    path('annonces/<int:pk>/<slug:slug>/', views.annonce_detail, name='annonce_detail'),
    path('annonces/<int:pk>/', views.annonce_detail_redirect, name='annonce_detail_old'),
    path('deposer/', views.deposer_annonce, name='deposer_annonce'),
    path('mes-annonces/', views.mes_annonces, name='mes_annonces'),
    path('mes-annonces/remonter/', views.remonter_annonces, name='remonter_annonces'),
    path('mes-messages/', views.mes_messages, name='mes_messages'),
    path('mes-messages/<int:annonce_pk>/supprimer/<int:other_user_pk>/', views.supprimer_conversation, name='supprimer_conversation'),
    path('mes-favoris/', views.mes_favoris, name='mes_favoris'),
    path('annonces/toggle-enregistrement/', views.toggle_enregistrement, name='toggle_enregistrement'),
    # SEO local : /annonces/<categorie>/<commune>/  (placé après les routes spécifiques /annonces/...)
    path('annonces/<slug:categorie>/<slug:commune>/', views.liste_par_ville, name='liste_par_ville'),
    path('tendances/', views.tendances, name='tendances'),
    path('info/', views.page_info, name='page_info'),
    path('business/', views.page_business, name='page_business'),
    path('admin-stats/', views.admin_stats, name='admin_stats'),
    path('admin-stats/export-csv/', views.export_csv, name='export_csv'),
    path('admin-sync-pa/', views.sync_pa_dashboard, name='sync_pa_dashboard'),
    path('admin-sync-pa/apply-engagement/', views.apply_engagement_stats, name='apply_engagement_stats'),
    path('mes-alertes/', views.mes_alertes, name='mes_alertes'),
    path('mes-alertes/creer/', views.creer_alerte, name='creer_alerte'),
    path('mes-alertes/<int:pk>/supprimer/', views.supprimer_alerte, name='supprimer_alerte'),
    path('mentions-legales/', views.mentions_legales, name='mentions_legales'),
    path('politique-confidentialite/', views.politique_confidentialite, name='politique_confidentialite'),
    path('cgu/', views.cgu, name='cgu'),
    path('api/impressions/', views.track_impressions, name='track_impressions'),
    # Boost paiement
    path('boost/paiement/<int:pk>/', views.boost_paiement, name='boost_paiement'),
    path('boost/paiement/<int:pk>/valider/', views.boost_paiement_valide_js, name='boost_paiement_valide_js'),
    path('boost/depuis-annonce/<int:pk>/', views.boost_from_edit, name='boost_from_edit'),
    path('boost/paiement/ipn/', views.boost_ipn, name='boost_ipn'),
    path('boost/paiement/succes/', views.boost_retour_succes, name='boost_retour_succes'),
    path('boost/paiement/echec/', views.boost_retour_echec, name='boost_retour_echec'),
    # Profil vendeur & notation
    path('vendeur/<int:user_id>/', views.profil_vendeur, name='profil_vendeur'),
    path('vendeur/<int:user_id>/noter/', views.noter_vendeur, name='noter_vendeur'),
    # Import depuis URL externe
    path('annonces/import-url/', views.import_url, name='import_url'),
]
