# ==============================================================================
# Shopping Cart Graph — Export des données de référence (CSV)
# Génère un fichier d'exemple structuré pour alimenter l'application ou les pipelines batch.
# ==============================================================================

import datetime
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


_configure_stdio_utf8()

_SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_NAME = "donnees_ventes.csv"


def generate_and_save_data(force: bool = False) -> int:
    """
    Produit un CSV de transactions (schéma compatible Shopping Cart Graph).
    Code retour : 0 = OK (export effectué ou fichier déjà présent sans --force), 1 = erreur d'écriture.
    """
    print("--- Export des données de référence ---")

    np.random.seed(42)
    nb_ventes = 1000

    base = datetime.datetime.today()
    date_list = [base - datetime.timedelta(days=x) for x in range(nb_ventes)]

    data = {
        "ID_Transaction": [f"TRX_{i}" for i in range(nb_ventes)],
        "Date": date_list,
        "Categorie_Produit": np.random.choice(
            ["Électronique", "Vêtements", "Maison", "Sports", "Livres"], nb_ventes
        ),
        "Prix_Unitaire": np.random.uniform(10, 500, nb_ventes),
        "Quantite": np.random.randint(1, 10, nb_ventes),
        "Âge_Client": np.random.randint(18, 70, nb_ventes),
        "Méthode_Paiement": np.random.choice(
            ["Carte Crédit", "PayPal", "Virement"], nb_ventes
        ),
        "Satisfaction_Client (1-5)": np.random.randint(1, 6, nb_ventes),
    }

    df = pd.DataFrame(data)

    for _ in range(25):
        df.loc[np.random.randint(0, nb_ventes), "Prix_Unitaire"] = np.nan
        df.loc[np.random.randint(0, nb_ventes), "Âge_Client"] = np.nan

    df = pd.concat([df, df.iloc[:15]], ignore_index=True)

    out_path = _SCRIPT_DIR / OUTPUT_NAME

    if out_path.exists() and not force:
        print(
            f"[INFO] '{OUTPUT_NAME}' existe déjà — aucun écrasement (comportement attendu).\n"
            "       Pour régénérer : python migrer_donnees.py --force"
        )
        return 0

    try:
        df.to_csv(out_path, index=False, encoding="utf-8")
        print(f"[OK] {len(df)} lignes enregistrées : {out_path}")
        print("     Fichier prêt pour l'application.")
        return 0
    except Exception as e:
        print(f"[ERREUR] Échec de l'export : {e}")
        return 1


if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        print(
            "Usage : python migrer_donnees.py [--force]\n"
            "  Sans --force : crée donnees_ventes.csv s'il n'existe pas ; sinon ne fait rien (code 0).\n"
            "  --force      : régénère le fichier même s'il existe déjà."
        )
        sys.exit(0)
    force = "--force" in sys.argv
    sys.exit(generate_and_save_data(force=force))
