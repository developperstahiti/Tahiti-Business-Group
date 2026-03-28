# ── Referentiel complet des localites de Polynesie francaise ──────────────────
# Structure : ARCHIPELS > ILES > COMMUNES > QUARTIERS/SECTIONS

LOCALITES = {
    "Iles de la Societe - Iles du Vent": {
        "Tahiti": {
            "Papeete": [
                "Centre-ville", "Paofai", "Tipaerui", "Mamao", "Fariipiti",
                "Fare Ute", "Motu Uta", "Sainte-Amelie", "Vallee Fautaua",
            ],
            "Pirae": ["Hamuta", "Orofara", "Fautaua", "Taaone"],
            "Arue": ["Temarii", "One Tree Hill", "RDO"],
            "Mahina": ["Onoiau", "Vaitupa", "Papenoo cote Mahina"],
            "Papenoo": [],
            "Hitiaa O Te Ra": ["Hitiaa", "Mahaena", "Tiarei", "Papenoo cote est"],
            "Taiarapu-Est": [
                "Afaahiti", "Faaone", "Pueu", "Tautira",
                "Taravao", "Plateau de Taravao",
            ],
            "Taiarapu-Ouest": [
                "Teahupoo", "Vairao", "Toahotu",
                "Saint-Joseph", "Fenuaino",
            ],
            "Teva I Uta": ["Papeari", "Mataiea"],
            "Papara": ["Papara centre", "Atimaono", "Mara"],
            "Paea": ["Paea centre", "Mapumai", "Orofara Paea"],
            "Punaauia": [
                "Punaauia centre", "Outumaoro", "Oropaa",
                "PK18", "PK20", "PK21", "Tamarii Faa'a", "Ah-Sing", "Manotahi",
            ],
            "Faa'a": [
                "Faa'a centre", "Maeva Beach", "Heiri", "Vaitea",
                "Pamatai", "Aeroport", "Motu Uta Faa'a",
            ],
        },
        "Moorea-Maiao": {
            "Afareaitu": [],
            "Papeatoai": [],
            "Haapiti": [],
            "Pao Pao": [],
            "Teavaro": [],
            "Maiao": [],
        },
    },
    "Iles de la Societe - Iles Sous-le-Vent": {
        "Raiatea": {
            "Uturoa": [],
            "Avera": [],
            "Fetuna": [],
            "Opoa": [],
            "Puohine": [],
            "Taputapuatea": [],
            "Tevaitoa": [],
        },
        "Tahaa": {
            "Haamene": [],
            "Hipu": [],
            "Patio": [],
            "Tiva": [],
            "Vaitoare": [],
        },
        "Bora-Bora": {
            "Anau": [],
            "Faanui": [],
            "Nunue": [],
            "Vaitape": [],
        },
        "Huahine": {
            "Fare": [],
            "Fitii": [],
            "Haapu": [],
            "Mahuti": [],
            "Maeva": [],
            "Parea": [],
            "Tefarerii": [],
        },
        "Maupiti": {
            "Farauru": [],
            "Haranae": [],
            "Vaiea": [],
        },
    },
    "Tuamotu-Gambier": {
        "Rangiroa": {"Rangiroa": []},
        "Fakarava": {"Fakarava": []},
        "Tikehau": {"Tikehau": []},
        "Manihi": {"Manihi": []},
        "Hao": {"Hao": []},
        "Tureia": {"Tureia": []},
        "Makatea": {"Makatea": []},
        "Arutua": {"Arutua": []},
        "Apataki": {"Apataki": []},
        "Kaukura": {"Kaukura": []},
        "Toau": {"Toau": []},
        "Gambier": {"Rikitea": []},
    },
    "Marquises": {
        "Nuku Hiva": {
            "Taiohae": [],
            "Hatiheu": [],
            "Taipivai": [],
            "Hooumi": [],
        },
        "Hiva Oa": {
            "Atuona": [],
            "Puamau": [],
        },
        "Ua Pou": {"Hakahau": []},
        "Ua Huka": {"Ua Huka": []},
        "Tahuata": {"Tahuata": []},
        "Fatu Hiva": {"Fatu Hiva": []},
    },
    "Australes": {
        "Rurutu": {"Rurutu": []},
        "Tubuai": {"Tubuai": []},
        "Raivavae": {"Raivavae": []},
        "Rimatara": {"Rimatara": []},
        "Rapa": {"Rapa": []},
    },
}

# Zones speciales Tahiti (pas des communes, mais utiles pour la recherche)
ZONES_SPECIALES = [
    "Plateau de Taravao",
    "Plateau de Mahina",
    "Vallee de la Papenoo",
    "Vallee de la Fautaua",
    "Cote Est",
    "Cote Ouest",
    "Presqu'ile",
]


def get_all_communes():
    """Retourne une liste plate de toutes les communes."""
    communes = []
    for archipel, iles in LOCALITES.items():
        for ile, commune_dict in iles.items():
            for commune in commune_dict:
                communes.append(commune)
    return sorted(set(communes))


def get_all_quartiers():
    """Retourne une liste plate de tous les quartiers."""
    quartiers = []
    for archipel, iles in LOCALITES.items():
        for ile, commune_dict in iles.items():
            for commune, qlist in commune_dict.items():
                quartiers.extend(qlist)
    return sorted(set(quartiers))


def get_communes_by_archipel():
    """Retourne {archipel: [communes...]} pour les selects dynamiques."""
    result = {}
    for archipel, iles in LOCALITES.items():
        communes = []
        for ile, commune_dict in iles.items():
            communes.extend(commune_dict.keys())
        result[archipel] = sorted(set(communes))
    return result


def get_quartiers_by_commune():
    """Retourne {commune: [quartiers...]} pour les selects dynamiques."""
    result = {}
    for archipel, iles in LOCALITES.items():
        for ile, commune_dict in iles.items():
            for commune, qlist in commune_dict.items():
                if commune in result:
                    result[commune].extend(qlist)
                else:
                    result[commune] = list(qlist)
    return result


def get_communes_choices():
    """Retourne les choices pour un champ Django (value, label)."""
    choices = [('', 'Toute la Polynesie')]
    for archipel, iles in LOCALITES.items():
        group = []
        for ile, commune_dict in iles.items():
            for commune in sorted(commune_dict.keys()):
                group.append((commune, commune))
        choices.append((archipel, group))
    return choices


def build_autocomplete_list():
    """Retourne une liste de tous les noms pour l'autocomplete."""
    names = set()
    for archipel, iles in LOCALITES.items():
        names.add(archipel)
        for ile, commune_dict in iles.items():
            names.add(ile)
            for commune, qlist in commune_dict.items():
                names.add(commune)
                names.update(qlist)
    names.update(ZONES_SPECIALES)
    # Ajouter PK0 a PK60
    for i in range(61):
        names.add(f"PK{i}")
        names.add(f"PK {i}")
    return sorted(names)
