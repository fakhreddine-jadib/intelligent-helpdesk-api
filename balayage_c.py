"""Rejoue le balayage du paramètre C et affiche les résultats."""

import joblib
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC

CORPUS = "data/processed/tickets_clean_en.csv"
VECTORISEUR = "models/tfidf_vectorizer.joblib"
VALEURS_C = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]

df = pd.read_csv(CORPUS)
x_train, x_test, y_train, y_test = train_test_split(
    df["text"].fillna(""), df["queue"],
    test_size=0.2, random_state=42, stratify=df["queue"],
)

vectoriseur = joblib.load(VECTORISEUR)
xtr = vectoriseur.transform(x_train)
xte = vectoriseur.transform(x_test)

scores = []
for c in VALEURS_C:
    modele = LinearSVC(C=c, class_weight="balanced", max_iter=5000)
    modele.fit(xtr, y_train)
    score = f1_score(y_test, modele.predict(xte), average="macro")
    scores.append(round(score, 4))
    print(f"  C = {c:<6} macro-F1 = {score:.4f}")

meilleur = max(range(len(scores)), key=lambda i: scores[i])

print("\n" + "=" * 60)
print("À copier dans generer_figures.py :\n")
print("BALAYAGE_C = {")
print(f'    "valeurs_c": {VALEURS_C},')
print(f'    "macro_f1": {scores},')
print(f'    "optimum_c": {VALEURS_C[meilleur]},')
print(f'    "optimum_f1": {scores[meilleur]},')
print("}")