"""
Génération des figures du rapport de stage — Intelligent Helpdesk
================================================================

Produit sept figures au format PDF vectoriel dans le dossier `figures/`,
prêtes à être déposées dans le dossier `images/` du projet Overleaf.

Utilisation
-----------
    python generer_figures.py

Trois figures se calculent directement depuis le corpus et les modèles.
Quatre demandent des valeurs déjà mesurées : elles sont regroupées dans
le bloc CONFIGURATION ci-dessous, à compléter avant exécution.

Chaque fonction peut être appelée séparément si toutes les données ne sont
pas disponibles en même temps — voir le bloc __main__ en fin de fichier.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# =====================================================================
#  CONFIGURATION — à adapter
# =====================================================================

# --- Chemins ---------------------------------------------------------
CHEMIN_CORPUS = "data/processed/tickets_clean_en.csv"
DOSSIER_SORTIE = Path("figures")

# Artefacts de modèles, nécessaires pour C5 et C6 uniquement.
CHEMIN_VECTORISEUR = "models/tfidf_vectorizer.joblib"
CHEMIN_MODELE_DEPT = "models/queue_classifier.joblib"

CHEMIN_ANNOTATIONS = "data/processed/gold_annotations.csv"
CHEMIN_MODELE_PRIO = "models/priority_classifier.joblib"

# --- Palette, alignée sur le préambule LaTeX -------------------------
BLEU = "#143C6E"
VERT = "#4A6741"
VIOLET = "#6B4C8A"
ROUGE = "#A83232"
GRIS = "#666666"

# --- Taxonomie -------------------------------------------------------
# Effectifs mesurés sur le corpus anglais nettoyé (11 923 tickets).
DEPARTEMENTS = [
    ("Technical Support", 3408),
    ("Product Support", 2230),
    ("Customer Service", 1856),
    ("IT Support", 1389),
    ("Billing and Payments", 1293),
    ("Returns and Exchanges", 580),
    ("Service Outages and Maintenance", 442),
    ("Sales and Pre-Sales", 330),
    ("Human Resources", 205),
    ("General Inquiry", 168),
]

# Intitulés raccourcis pour les axes, les noms complets débordant.
ABREGE = {
    "Technical Support": "Technical Support",
    "Product Support": "Product Support",
    "Customer Service": "Customer Service",
    "IT Support": "IT Support",
    "Billing and Payments": "Billing",
    "Returns and Exchanges": "Returns",
    "Service Outages and Maintenance": "Service Outages",
    "Sales and Pre-Sales": "Sales",
    "Human Resources": "HR",
    "General Inquiry": "General Inquiry",
}

# --- À COMPLÉTER : balayage du paramètre C (figure C4) ---------------
# Reprendre les valeurs du carnet d'entraînement.
BALAYAGE_C = {
    "valeurs_c": [1.0, 2.0, 4.0, 8.0, 16.0, 32.0],
    "macro_f1": [0.5227, 0.5327, 0.5336, 0.5339, 0.5339, 0.5312],
    "optimum_c": 4.0,
    "optimum_f1": 0.5336,
}

# --- À COMPLÉTER : étude d'annotation manuelle (figure C7) -----------
# Matrice 3x3 des effectifs : lignes = priorité annotée manuellement,
# colonnes = priorité prédite par le modèle. Total = 300 tickets.
# Deux valeurs sont connues : 83 tickets annotés « élevée », dont 4
# classés « faible » par le modèle et environ 47 classés « élevée »
# (56,6 % de 83). Les autres cellules sont à relever dans le carnet.
# --- Point de fonctionnement du routage (figure C6) ------------------
SEUIL_RETENU = 0.5
COUVERTURE_AU_SEUIL = 0.31
FIABILITE_AU_SEUIL = 0.808


# =====================================================================
#  Style commun
# =====================================================================

def appliquer_style():
    """Réglages partagés par toutes les figures."""
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "axes.edgecolor": "#CCCCCC",
        "axes.titlecolor": BLEU,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.15,
        "grid.color": "#E8E8E8",
        "grid.linewidth": 0.6,
    })


def enregistrer(fig, nom):
    """Écrit la figure en PDF vectoriel dans le dossier de sortie."""
    DOSSIER_SORTIE.mkdir(exist_ok=True)
    chemin = DOSSIER_SORTIE / f"{nom}.pdf"
    fig.savefig(chemin)
    plt.close(fig)
    print(f"  écrit : {chemin}")


def charger_corpus():
    """Charge le corpus anglais déjà nettoyé."""
    df = pd.read_csv(CHEMIN_CORPUS)
    df["texte"] = df["text"].fillna("")
    return df


# =====================================================================
#  C1 — Distribution des tickets par département
# =====================================================================

def figure_distrib_dept():
    """Barres horizontales, triées par effectif décroissant."""
    noms = [ABREGE[n] for n, _ in DEPARTEMENTS]
    effectifs = [e for _, e in DEPARTEMENTS]
    total = sum(effectifs)

    fig, ax = plt.subplots(figsize=(8, 4.5))

    # La classe majoritaire et la minoritaire portent le rapport 20,3:1 :
    # on les distingue pour que l'écart se lise immédiatement.
    couleurs = [BLEU] * len(noms)
    couleurs[0] = "#0E2C52"
    couleurs[-1] = ROUGE

    barres = ax.barh(noms, effectifs, color=couleurs, height=0.68)
    ax.invert_yaxis()

    for barre, effectif in zip(barres, effectifs):
        part = 100 * effectif / total
        ax.text(
            barre.get_width() + total * 0.008,
            barre.get_y() + barre.get_height() / 2,
            f"{effectif:,}".replace(",", " ") + f"  ({part:.1f} %)",
            va="center", fontsize=9, color="#333333",
        )

    ax.set_xlabel("Nombre de tickets")
    ax.set_xlim(0, max(effectifs) * 1.28)
    ax.set_title("Répartition des tickets par département")
    ax.grid(axis="y", visible=False)

    ax.annotate(
        "Rapport de déséquilibre : 20,3 : 1",
        xy=(0.62, 0.12), xycoords="axes fraction",
        fontsize=9, color=ROUGE, style="italic",
    )

    enregistrer(fig, "distrib_dept")


# =====================================================================
#  C2 — Longueur des textes par département
# =====================================================================

def figure_longueur_dept(df=None):
    """Boîtes à moustaches : le propos est l'absence d'écart."""
    if df is None:
        df = charger_corpus()

    df = df.copy()
    df["longueur"] = df["texte"].str.split().str.len()
    df["dept"] = df["queue"].map(ABREGE).fillna(df["queue"])

    ordre = [ABREGE[n] for n, _ in DEPARTEMENTS]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.boxplot(
        data=df, y="dept", x="longueur", order=ordre,
        color="#DCE6F2", linecolor=BLEU, linewidth=1.1,
        fliersize=1.5, ax=ax,
    )

    mediane_globale = df["longueur"].median()
    ax.axvline(mediane_globale, color=ROUGE, linestyle="--", linewidth=1.2)
    ax.annotate(
        f"Médiane globale : {mediane_globale:.0f} mots",
        xy=(mediane_globale, len(ordre) - 0.4),
        xytext=(8, 0), textcoords="offset points",
        fontsize=9, color=ROUGE, style="italic", va="center",
    )

    ax.set_xlabel("Longueur du ticket (nombre de mots)")
    ax.set_ylabel("")
    ax.set_title("Longueur des tickets par département")
    ax.grid(axis="y", visible=False)

    enregistrer(fig, "longueur_dept")


# =====================================================================
#  C3 — Répartition des priorités par département
# =====================================================================

def figure_heatmap_prio(df=None):
    """Carte de chaleur 10 x 3, normalisée par ligne."""
    if df is None:
        df = charger_corpus()

    ordre_dept = [n for n, _ in DEPARTEMENTS]
    ordre_prio = ["high", "medium", "low"]
    etiquettes_prio = ["Élevée", "Moyenne", "Faible"]

    tableau = pd.crosstab(df["queue"], df["priority"], normalize="index") * 100
    tableau = tableau.reindex(index=ordre_dept, columns=ordre_prio)
    tableau.index = [ABREGE[n] for n in ordre_dept]
    tableau.columns = etiquettes_prio

    fig, ax = plt.subplots(figsize=(6.5, 5))
    sns.heatmap(
        tableau, annot=True, fmt=".0f", cmap="Blues",
        cbar_kws={"label": "Part des tickets du département (%)"},
        linewidths=0.6, linecolor="white",
        annot_kws={"fontsize": 9}, ax=ax,
    )

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("Répartition des priorités par département")
    plt.setp(ax.get_yticklabels(), rotation=0)

    enregistrer(fig, "heatmap_prio")


# =====================================================================
#  C4 — Balayage du paramètre de régularisation
# =====================================================================

def figure_balayage_c():
    """Courbe de la macro-moyenne F1 en fonction de C."""
    valeurs = BALAYAGE_C["valeurs_c"]
    scores = BALAYAGE_C["macro_f1"]

    if any(s is None for s in scores):
        print("  IGNORÉ : compléter BALAYAGE_C['macro_f1'] avant exécution.")
        return

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(valeurs, scores, marker="o", color=BLEU,
            linewidth=1.8, markersize=5)

    c_opt = BALAYAGE_C["optimum_c"]
    f1_opt = BALAYAGE_C["optimum_f1"]
    ax.plot(c_opt, f1_opt, marker="o", color=ROUGE, markersize=9, zorder=5)
    ax.annotate(
        f"Valeur retenue : C = {c_opt:.0f}\nmacro-F1 = {f1_opt:.3f}".replace(".", ","),
        xy=(c_opt, f1_opt), xytext=(20, -30), textcoords="offset points",
        fontsize=9, color=ROUGE,
        arrowprops=dict(arrowstyle="->", color=ROUGE, linewidth=1),
    )

    ax.set_xscale("log")
    ax.set_xlabel("Paramètre de régularisation $C$ (échelle logarithmique)")
    ax.set_ylabel("Macro-moyenne $F_1$")
    ax.set_title("Effet de la régularisation sur la performance")

    enregistrer(fig, "balayage_c")


# =====================================================================
#  C5 — Matrice de confusion du modèle de département
# =====================================================================

def figure_matrice_confusion(y_vrai=None, y_predit=None):
    """Matrice 10 x 10 normalisée par ligne.

    Passer y_vrai et y_predit depuis le carnet d'évaluation. À défaut,
    la fonction tente de recharger les modèles et de rejouer la
    prédiction sur le jeu de test.
    """
    if y_vrai is None or y_predit is None:
        try:
            import joblib
            from sklearn.model_selection import train_test_split

            df = charger_corpus()
            _, x_test, _, y_vrai = train_test_split(
                df["texte"], df["queue"], test_size=0.2,
                random_state=42, stratify=df["queue"],
            )
            vectoriseur = joblib.load(CHEMIN_VECTORISEUR)
            modele = joblib.load(CHEMIN_MODELE_DEPT)
            y_predit = modele.predict(vectoriseur.transform(x_test))
        except Exception as erreur:
            print(f"  IGNORÉ : impossible de recharger les modèles ({erreur}).")
            print("  Appeler figure_matrice_confusion(y_test, y_pred) "
                  "depuis le carnet.")
            return

    from sklearn.metrics import confusion_matrix

    ordre = [n for n, _ in DEPARTEMENTS]
    matrice = confusion_matrix(y_vrai, y_predit, labels=ordre, normalize="true")
    matrice = matrice * 100

    etiquettes = [ABREGE[n] for n in ordre]
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    sns.heatmap(
        matrice, annot=True, fmt=".0f", cmap="Blues",
        xticklabels=etiquettes, yticklabels=etiquettes,
        cbar_kws={"label": "Part de la classe réelle (%)"},
        linewidths=0.5, linecolor="white",
        annot_kws={"fontsize": 8}, ax=ax,
    )

    # Encadré sur le bloc des trois files de support, dont la confusion
    # motive l'expérience de fusion présentée au chapitre 3.
    from matplotlib.patches import Rectangle
    indices = [ordre.index("Technical Support"),
               ordre.index("Product Support"),
               ordre.index("IT Support")]
    for i in indices:
        for j in indices:
            ax.add_patch(Rectangle((j, i), 1, 1, fill=False,
                                   edgecolor=ROUGE, linewidth=1.6))

    ax.set_xlabel("Département prédit")
    ax.set_ylabel("Département réel")
    ax.set_title("Matrice de confusion du modèle de département")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    plt.setp(ax.get_yticklabels(), rotation=0)

    enregistrer(fig, "matrice_confusion")


# =====================================================================
#  C6 — Arbitrage entre couverture et fiabilité
# =====================================================================

def figure_courbe_seuil(y_vrai=None, y_predit=None, probabilites=None):
    """Deux courbes en fonction du seuil de confiance."""
    if any(x is None for x in (y_vrai, y_predit, probabilites)):
        try:
            import joblib
            from sklearn.model_selection import train_test_split

            df = charger_corpus()
            _, x_test, _, y_vrai = train_test_split(
                df["texte"], df["queue"], test_size=0.2,
                random_state=42, stratify=df["queue"],
            )
            vectoriseur = joblib.load(CHEMIN_VECTORISEUR)
            modele = joblib.load(CHEMIN_MODELE_DEPT)
            x_vectorise = vectoriseur.transform(x_test)
            y_predit = modele.predict(x_vectorise)
            probabilites = modele.predict_proba(x_vectorise)
        except Exception as erreur:
            print(f"  IGNORÉ : {erreur}")
            return
        
    confiance = np.max(probabilites, axis=1)
    correct = np.array(y_vrai) == np.array(y_predit)

    seuils = np.linspace(0.1, 0.9, 81)
    couverture, fiabilite = [], []
    for seuil in seuils:
        retenus = confiance >= seuil
        couverture.append(retenus.mean())
        fiabilite.append(correct[retenus].mean() if retenus.any() else np.nan)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(seuils, np.array(couverture) * 100, color=BLEU,
            linewidth=2, label="Couverture — tickets routés automatiquement")
    ax.plot(seuils, np.array(fiabilite) * 100, color=VERT,
            linewidth=2, label="Fiabilité — décisions correctes parmi eux")

    ax.axvline(SEUIL_RETENU, color=ROUGE, linestyle="--", linewidth=1.2)
    ax.annotate(
        f"Seuil retenu : {SEUIL_RETENU}".replace(".", ",")
        + f"\n{COUVERTURE_AU_SEUIL:.0%} des tickets"
        + f"\nfiabilité {FIABILITE_AU_SEUIL:.1%}".replace(".", ","),
        xy=(SEUIL_RETENU, 50), xytext=(18, 10), textcoords="offset points",
        fontsize=9, color=ROUGE,
    )

    ax.set_xlabel("Seuil de confiance")
    ax.set_ylabel("Pourcentage")
    ax.set_ylim(0, 105)
    ax.set_title("Arbitrage entre couverture et fiabilité du routage")
    ax.legend(loc="lower left", frameon=True, fontsize=9)

    enregistrer(fig, "courbe_seuil")


# =====================================================================
#  C7 — Concordance des priorités, annotation contre modèle
# =====================================================================

def figure_concordance_prio():
    """Matrice 3 x 3 : priorité annotée contre priorité prédite."""
    import joblib
    from sklearn.metrics import confusion_matrix

    try:
        annotations = pd.read_csv(CHEMIN_ANNOTATIONS)
        vectoriseur = joblib.load(CHEMIN_VECTORISEUR)
        modele = joblib.load(CHEMIN_MODELE_PRIO)
    except Exception as erreur:
        print(f"  IGNORÉ : {erreur}")
        return

    textes = annotations["text"].fillna("")
    predites = modele.predict(vectoriseur.transform(textes))
    annotees = annotations["my_priority"]

    ordre = ["high", "medium", "low"]
    etiquettes = ["Élevée", "Moyenne", "Faible"]
    matrice = confusion_matrix(annotees, predites, labels=ordre)

    fig, ax = plt.subplots(figsize=(5.8, 4.6))
    sns.heatmap(
        matrice, annot=True, fmt="d", cmap="Blues",
        xticklabels=etiquettes, yticklabels=etiquettes,
        cbar_kws={"label": "Nombre de tickets"},
        linewidths=0.6, linecolor="white",
        annot_kws={"fontsize": 11}, ax=ax,
    )

    # La case « annoté élevée / prédit faible » porte le 4,8 % du texte.
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((2, 0), 1, 1, fill=False,
                           edgecolor=ROUGE, linewidth=2.2))

    ax.set_xlabel("Priorité prédite par le modèle")
    ax.set_ylabel("Priorité attribuée par l'annotateur")
    ax.set_title("Concordance des priorités sur l'échantillon annoté")
    plt.setp(ax.get_yticklabels(), rotation=0)

    # Contrôle : les valeurs citées dans le rapport doivent se retrouver ici.
    total_elevee = matrice[0].sum()
    print(f"    tickets annotés « élevée » : {total_elevee}")
    print(f"    détectés comme tels : {matrice[0][0]} "
          f"({100 * matrice[0][0] / total_elevee:.1f} %)")
    print(f"    relégués en « faible » : {matrice[0][2]} "
          f"({100 * matrice[0][2] / total_elevee:.1f} %)")

    enregistrer(fig, "concordance_prio")


# =====================================================================
#  Exécution
# =====================================================================

if __name__ == "__main__":
    appliquer_style()
    print("Génération des figures\n")

    print("C1 — distribution par département")
    figure_distrib_dept()

    corpus = None
    try:
        corpus = charger_corpus()
    except FileNotFoundError:
        print("\n  Corpus introuvable : vérifier CHEMIN_CORPUS.")
        print("  Les figures C2 et C3 sont ignorées.\n")

    if corpus is not None:
        print("C2 — longueur des tickets")
        figure_longueur_dept(corpus)
        print("C3 — priorités par département")
        figure_heatmap_prio(corpus)

    print("C4 — balayage du paramètre C")
    figure_balayage_c()

    print("C5 — matrice de confusion")
    figure_matrice_confusion()

    print("C6 — couverture et fiabilité")
    figure_courbe_seuil()

    print("C7 — concordance des priorités")
    figure_concordance_prio()

    print(f"\nTerminé. Figures écrites dans : {DOSSIER_SORTIE.resolve()}")