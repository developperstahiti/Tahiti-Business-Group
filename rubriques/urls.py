from django.urls import path
from . import views

urlpatterns = [
    path('', views.rubriques_index, name='rubriques_index'),
    path('promo/deposer/', views.deposer_promo, name='deposer_promo'),
    path('info/deposer/', views.deposer_info, name='deposer_info'),
    path('nouveaute/deposer/', views.deposer_nouveaute, name='deposer_nouveaute'),
    path('promo/<int:pk>/', views.promo_detail, name='promo_detail'),
    path('info/<int:pk>/', views.info_detail, name='info_detail'),
    path('nouveaute/<int:pk>/', views.nouveaute_detail, name='nouveaute_detail'),
    path('moderation/', views.moderation_dashboard, name='moderation_dashboard'),
    path('moderation/<str:type_article>/<int:pk>/<str:action>/',
         views.moderer_article, name='moderer_article'),
]