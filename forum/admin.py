from django.contrib import admin
from .models import Sujet, Reponse, Vote


@admin.register(Sujet)
class SujetAdmin(admin.ModelAdmin):
    list_display = ['titre', 'auteur', 'nb_votes', 'nb_vues', 'est_epingle', 'est_ferme', 'date_creation']
    list_filter = ['est_epingle', 'est_ferme']
    list_editable = ['est_epingle', 'est_ferme']
    search_fields = ['titre', 'contenu']
    actions = ['epingler', 'desepingler', 'fermer', 'ouvrir']

    def epingler(self, request, qs): qs.update(est_epingle=True)
    epingler.short_description = "📌 Épingler"

    def desepingler(self, request, qs): qs.update(est_epingle=False)
    desepingler.short_description = "Désépingler"

    def fermer(self, request, qs): qs.update(est_ferme=True)
    fermer.short_description = "🔒 Fermer"

    def ouvrir(self, request, qs): qs.update(est_ferme=False)
    ouvrir.short_description = "🔓 Ouvrir"


@admin.register(Reponse)
class ReponseAdmin(admin.ModelAdmin):
    list_display = ['auteur', 'sujet', 'nb_votes', 'date_creation']
    list_filter = ['date_creation']


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'type_objet', 'objet_id', 'valeur']
