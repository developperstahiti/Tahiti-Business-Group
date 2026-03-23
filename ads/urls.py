from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('annonces/', views.liste_annonces, name='liste_annonces'),
    path('annonces/<int:pk>/', views.annonce_detail, name='annonce_detail'),
    path('deposer/', views.deposer_annonce, name='deposer_annonce'),
    path('mes-annonces/', views.mes_annonces, name='mes_annonces'),
    path('annonces/<int:pk>/edit/', views.edit_annonce, name='edit_annonce'),
    path('annonces/<int:pk>/supprimer/', views.supprimer_annonce, name='supprimer_annonce'),
    path('annonces/<int:pk>/vendu/', views.marquer_vendu, name='marquer_vendu'),
    path('annonces/<int:pk>/contact/', views.contact_annonce, name='contact_annonce'),
    path('annonces/<int:pk>/signaler/', views.signaler_annonce, name='signaler_annonce'),
    path('mes-messages/', views.mes_messages, name='mes_messages'),
    path('mes-favoris/', views.mes_favoris, name='mes_favoris'),
    path('info/', views.page_info, name='page_info'),
    path('business/', views.page_business, name='page_business'),
    path('admin-stats/', views.admin_stats, name='admin_stats'),
    path('admin-stats/export-csv/', views.export_csv, name='export_csv'),
    path('mes-alertes/', views.mes_alertes, name='mes_alertes'),
    path('mes-alertes/creer/', views.creer_alerte, name='creer_alerte'),
    path('mes-alertes/<int:pk>/supprimer/', views.supprimer_alerte, name='supprimer_alerte'),
    path('mentions-legales/', views.mentions_legales, name='mentions_legales'),
    path('cgu/', views.cgu, name='cgu'),
    path('api/impressions/', views.track_impressions, name='track_impressions'),
]
