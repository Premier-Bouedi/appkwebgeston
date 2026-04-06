# ==============================================================================
# Shopping Cart Graph — Entraînement batch du modèle de prévision
# Lit donnees_ventes.csv (dossier du script) et écrit modele_ia.pkl.
# Les colonnes d'entrée du modèle doivent rester alignées avec app.py (MODEL_FEATURES).
# ==============================================================================

from __future__ import annotations

import io
import pickle
import sys
import unicodedata
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

# Aligné sur app.py (inférence)
FEATURE_COLUMNS: tuple[str, ...] = ("Âge_Client", "Quantite")
TARGET_COLUMN = "Montant_Total"

REQUIRED_FOR_CLEANING = frozenset({"Prix_Unitaire", "Quantite", "Âge_Client"})
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_FILENAME = "donnees_ventes.csv"
MODEL_FILENAME = "modele_ia.pkl"


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """NFC + strip : évite les écarts de nom (ex. Âge_Client) entre exports."""
    out = df.copy()
    out.columns = [unicodedata.normalize("NFC", str(c)).strip() for c in out.columns]
    return out


def _read_csv_flexible(path: Path) -> pd.DataFrame:
    """CSV : encodages usuels + séparateurs `,` et `;`."""
    raw = path.read_bytes()
    last_err: Optional[Exception] = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError as e:
            last_err = e
            continue
        for sep in (",", ";"):
            try:
                df = pd.read_csv(io.StringIO(text), sep=sep)
            except Exception as e:
                last_err = e
                continue
            if len(df.columns) < 2 and len(df) > 0:
                continue
            return _normalize_column_names(df)
    if last_err:
        raise last_err
    raise ValueError("Aucun encodage ou séparateur valide pour ce fichier.")


def _prepare_training_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyage + Montant_Total + lignes finies (même logique métier que l'app)."""
    if not REQUIRED_FOR_CLEANING.issubset(df.columns):
        missing = REQUIRED_FOR_CLEANING - set(df.columns)
        raise ValueError(f"Colonnes manquantes : {sorted(missing)}")

    work = df.copy()
    for col in REQUIRED_FOR_CLEANING:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    work = work.drop_duplicates().dropna(subset=sorted(REQUIRED_FOR_CLEANING))
    work[TARGET_COLUMN] = work["Prix_Unitaire"] * work["Quantite"]
    mask = np.isfinite(work[TARGET_COLUMN].to_numpy(dtype=float))
    work = work.loc[mask].reset_index(drop=True)
    return work


def _verify_model_file(path: Path) -> bool:
    """Contrôle que le pickle se recharge et accepte une prédiction minimale."""
    try:
        with open(path, "rb") as f:
            model = pickle.load(f)
        sample = pd.DataFrame(
            {FEATURE_COLUMNS[0]: [35.0], FEATURE_COLUMNS[1]: [2.0]}
        )
        pred = model.predict(sample)
        return np.isfinite(pred).all()
    except Exception:
        return False


def main() -> int:
    _configure_stdio_utf8()
    print("--- Entraînement du modèle de prévision ---")

    csv_path = SCRIPT_DIR / DATA_FILENAME
    if not csv_path.is_file():
        print(
            f"[ERREUR] '{DATA_FILENAME}' introuvable dans {SCRIPT_DIR}\n"
            "        Exécutez : python migrer_donnees.py"
        )
        return 1

    try:
        df = _read_csv_flexible(csv_path)
    except OSError as e:
        print(f"[ERREUR] Lecture disque : {e}")
        return 1
    except Exception as e:
        print(
            f"[ERREUR] Impossible de parser '{DATA_FILENAME}' : {e}\n"
            "        Régénérez : python migrer_donnees.py --force"
        )
        return 1

    if not REQUIRED_FOR_CLEANING.issubset(df.columns):
        print(
            "[ERREUR] Colonnes requises manquantes.\n"
            f"        Présentes : {list(df.columns)}\n"
            f"        Requis    : {sorted(REQUIRED_FOR_CLEANING)}"
        )
        return 1

    if len(df) == 0:
        print("[ERREUR] Le CSV ne contient aucune ligne.")
        return 1

    print(f"Données chargées : {len(df)} ligne(s).")

    try:
        df_cleaned = _prepare_training_frame(df)
    except ValueError as e:
        print(f"[ERREUR] {e}")
        return 1

    n = len(df_cleaned)
    print(f"Données nettoyées : {n} ligne(s).")

    if n < 2:
        print(
            "[ERREUR] Moins de 2 lignes exploitables après nettoyage.\n"
            "        Vérifiez le CSV ou : python migrer_donnees.py --force"
        )
        return 1

    X = df_cleaned[list(FEATURE_COLUMNS)]
    y = df_cleaned[TARGET_COLUMN]

    if n < 10:
        print("[AVERTISSEMENT] Peu d'exemples : métriques peu fiables.")

    if n < 5:
        X_train = X_test = X
        y_train = y_test = y
        print(
            "[AVERTISSEMENT] n < 5 : entraînement et test identiques (métriques indicatives)."
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

    mse = mean_squared_error(y_test, y_pred)
    y_test_arr = np.asarray(y_test, dtype=float)
    if len(y_test_arr) < 2 or float(np.var(y_test_arr, ddof=0)) < 1e-15:
        r2 = float("nan")
        print("[AVERTISSEMENT] R² non calculable (variance nulle ou échantillon trop petit).")
    else:
        r2 = float(r2_score(y_test, y_pred))

    print("[OK] Évaluation :")
    print(f"   - MSE : {mse:,.2f}")
    if np.isfinite(r2):
        print(f"   - R²  : {r2:.4f}")
    else:
        print("   - R²  : N/A")

    model_path = SCRIPT_DIR / MODEL_FILENAME
    try:
        with open(model_path, "wb") as f:
            pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)
    except OSError as e:
        print(f"[ERREUR] Écriture du modèle : {e}")
        return 1

    if not _verify_model_file(model_path):
        print("[ERREUR] Le fichier modèle a été écrit mais la vérification post-écriture a échoué.")
        return 1

    print(f"[OK] Modèle enregistré : {model_path}")
    print("--- Fin du pipeline d'entraînement ---")
    return 0


def _print_help() -> None:
    print(
        "Usage : python entrainer_ia.py\n\n"
        f"  Entrée  : {SCRIPT_DIR / DATA_FILENAME}\n"
        f"  Sortie  : {SCRIPT_DIR / MODEL_FILENAME}\n"
        f"  Features: {list(FEATURE_COLUMNS)} → {TARGET_COLUMN}\n\n"
        "  Code retour : 0 = succès, 1 = erreur."
    )


if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        _print_help()
        sys.exit(0)
    sys.exit(main())
