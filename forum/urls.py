from django.urls import path
from . import views

urlpatterns = [
    path('', views.forum_index, name='forum_index'),
    path('creer/', views.creer_sujet, name='forum_creer_sujet'),
    path('s/<slug:slug>/', views.detail_sujet, name='forum_sujet'),
    path('vote/', views.forum_vote, name='forum_vote'),
    path('mes-sujets/', views.mes_sujets, name='forum_mes_sujets'),
    path('s/<slug:slug>/moderer/', views.moderer_sujet, name='forum_moderer_sujet'),
]
