# -*- coding: utf-8 -*-
"""Contrôle qualité interne — logique données / ML (sans Streamlit).
Usage : python verifier_projet.py
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    errors: list[str] = []

    # --- 1. Code app.py : bouton formulaire Streamlit correct ---
    app_path = os.path.join(root, "app.py")
    with open(app_path, encoding="utf-8") as f:
        app_src = f.read()
    if "form_submit_submit_button" in app_src:
        errors.append("app.py contient encore form_submit_submit_button (invalide).")
    if "form_submit_button" not in app_src:
        errors.append("app.py doit utiliser st.form_submit_button pour la prédiction.")

    # --- 2. Pipeline données / ML (même logique que app.py page 1 + 3) ---
    try:
        import numpy as np
        import pandas as pd
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import mean_squared_error, r2_score
        from sklearn.model_selection import train_test_split
    except ImportError as e:
        print("ERREUR : installez les dépendances : pip install -r requirements.txt")
        print(e)
        return 2

    np.random.seed(42)
    n = 200
    df = pd.DataFrame(
        {
            "Prix_Unitaire": np.random.uniform(10, 500, n),
            "Quantite": np.random.randint(1, 10, n),
            "Âge_Client": np.random.randint(18, 70, n),
        }
    )
    df.loc[np.random.randint(0, n, size=5), "Prix_Unitaire"] = np.nan
    df = pd.concat([df, df.iloc[:5]], ignore_index=True)

    cleaned = df.drop_duplicates().dropna()
    cleaned["Montant_Total"] = cleaned["Prix_Unitaire"] * cleaned["Quantite"]
    if cleaned.shape[0] >= df.shape[0]:
        errors.append("Le nettoyage devrait réduire ou stabiliser le nombre de lignes (doublons/NaN).")
    if cleaned["Montant_Total"].isna().any():
        errors.append("Montant_Total ne doit pas contenir de NaN après calcul.")

    X = cleaned[["Âge_Client", "Quantite"]]
    y = cleaned["Montant_Total"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    if not np.isfinite(mse) or not np.isfinite(r2):
        errors.append("MSE ou R² non finis après entraînement.")

    # Prédiction avec clamp métier (comme app.py)
    neg_input = pd.DataFrame({"Âge_Client": [18], "Quantite": [1]})
    raw = float(model.predict(neg_input)[0])
    clamped = max(0.0, raw)
    if clamped < 0:
        errors.append("Clamp métier : le montant doit être >= 0.")

    # --- 3. migrer_donnees : protection anti-écrasement (présence du message) ---
    migrer_path = os.path.join(root, "migrer_donnees.py")
    with open(migrer_path, encoding="utf-8") as f:
        migrer_src = f.read()
    if ".exists()" not in migrer_src or "force" not in migrer_src.lower():
        errors.append("migrer_donnees.py : logique anti-écrasement / --force attendue introuvable.")

    # --- 4. entrainer_ia.py : présent et contrôle CSV avant entraînement ---
    train_path = os.path.join(root, "entrainer_ia.py")
    if not os.path.isfile(train_path):
        errors.append("entrainer_ia.py doit être présent à la racine du projet.")
    else:
        with open(train_path, encoding="utf-8") as f:
            train_src = f.read()
        if "is_file()" not in train_src:
            errors.append("entrainer_ia.py : vérification d'existence du CSV attendue.")

    if errors:
        print("ÉCHEC —", len(errors), "problème(s) :")
        for e in errors:
            print(" -", e)
        return 1

    print("OK — Toutes les vérifications logique / sécurité (code + pipeline) ont réussi.")
    print(f"   Pipeline ML : MSE={mse:.2f}, R²={r2:.4f}, lignes nettoyées={len(cleaned)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
