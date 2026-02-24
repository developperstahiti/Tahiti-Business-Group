from django.urls import path
from . import views

urlpatterns = [
    path('tarifs/',              views.tarifs_pubs,    name='tarifs_pubs'),
    path('demande/',             views.demande_pub,    name='demande_pub'),
    path('creer/',               views.pub_creer,      name='pub_creer'),
    path('<int:pk>/modifier/',   views.pub_modifier,   name='pub_modifier'),
    path('<int:pk>/supprimer/',  views.pub_supprimer,  name='pub_supprimer'),
    path('<int:pk>/toggle/',     views.pub_toggle,     name='pub_toggle'),
]