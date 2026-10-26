"""Séance Python (aucune bibliothèque à installer) : version pédagogique du filtre.
L'extension utilise JavaScript ; ce script Python permet de comparer les deux.
Exécuter : python atelier_python.py
"""

VIDEOS = [
    "Skibidi sigma brainrot compilation",
    "Motivation et discipline : progresser chaque jour",
    "Documentaire : l'histoire de Rome",
    "Intelligence artificielle et réseaux de neurones",
    "Twerk dance viral",
    "La place des femmes dans les mathématiques",
]

MOTS_CLES = {
    "brainrot": ["brainrot", "skibidi", "sigma", "rizz"],
    "motivation": ["motivation", "discipline", "mindset"],
    "culture": ["histoire", "documentaire", "philosophie"],
    "science": ["mathématiques", "intelligence artificielle", "python"],
    "suggestif": ["twerk", "thirst trap", "sexy dance"],
}


def classer_video(titre):
    """Retourne une catégorie ou 'autre'."""
    titre = titre.lower()
    for categorie, mots in MOTS_CLES.items():
        for mot in mots:
            if mot in titre:
                return categorie
    return "autre"


def filtrer(videos, categorie, mode="only"):
    """mode='only' : conserver, mode='hide' : masquer, mode='all' : tout."""
    resultat = []
    for titre in videos:
        type_video = classer_video(titre)
        garder = (mode == "all" or
                  (mode == "only" and type_video == categorie) or
                  (mode == "hide" and type_video != categorie))
        if garder:
            resultat.append(titre)
    return resultat


if __name__ == "__main__":
    for mode in ("all", "hide", "only"):
        print(f"\nMODE : {mode}")
        for video in filtrer(VIDEOS, "brainrot", mode):
            print("-", video)

    # À FAIRE : ajoute le mot-clé 'procrastination' dans la catégorie motivation.
    # À FAIRE : compare 'only' culture et 'only' motivation.
