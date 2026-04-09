# ==============================================================================
# Shopping Cart Graph — Entraînement batch du modèle de prévision
# Utilise le nouveau moteur Auto-ML (ModelManager) pour l'optimisation.
# ==============================================================================

from __future__ import annotations

import io
import sys
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd
from src.model_manager import ModelManager

# Les colonnes requises de base
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
    """CSV : encodages usuels + séparateurs "," et ";"."""
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
    if "Montant_Total" not in work.columns:
        work["Montant_Total"] = work["Prix_Unitaire"] * work["Quantite"]
        
    mask = pd.notna(work["Montant_Total"])
    work = work.loc[mask].reset_index(drop=True)
    return work

def main() -> int:
    _configure_stdio_utf8()
    print("--- Entraînement 🚀 Auto-ML Premium (Vision-ShopFlow) ---")

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

    print(f"Données brutes chargées : {len(df)} ligne(s).")

    try:
        df_cleaned = _prepare_training_frame(df)
    except ValueError as e:
        print(f"[ERREUR] {e}")
        return 1

    n = len(df_cleaned)
    print(f"Données nettoyées exploitables : {n} ligne(s).")

    if n < 5:
        print(
            "[ERREUR] Moins de 5 lignes exploitables après nettoyage.\n"
            "Modèles ML désactivés par manque d'exemples."
        )
        return 1

    # Utilisation du nouveau ModelManager Premium
    model_path = SCRIPT_DIR / MODEL_FILENAME
    manager = ModelManager(model_path)
    
    print("\nLancement du GridSearch & Compétition des algorithmes...")
    manager.auto_train(df_cleaned)
    
    if manager.model is None:
        print("[ERREUR] L'entraînement a échoué.")
        return 1

    print("\n[OK] Évaluation du meilleur modèle :")
    print(f"   - Algorithme Vainqueur : {manager.metrics.get('best_algo')}")
    print(f"   - MSE : {manager.metrics.get('mse', 0):,.2f}")
    
    r2 = manager.metrics.get("r2", 0)
    print(f"   - R²  : {r2:.4f} ({r2*100:.1f}% de précision)")
    
    importances = manager.get_top_features(3)
    if importances:
        print("\n[INTELLIGENCE] Variables les plus influentes :")
        for feature, imp in importances.items():
            print(f"   - {feature:20s}: {imp:.1f}%")

    print(f"\n[OK] Modèle persistant Premium sauvegardé : {model_path.name}")
    print("--- Fin du pipeline d'entraînement ---")
    return 0

def _print_help() -> None:
    print(
        "Usage : python entrainer_ia.py\n\n"
        f"  Entrée  : {SCRIPT_DIR / DATA_FILENAME}\n"
        f"  Sortie  : {SCRIPT_DIR / MODEL_FILENAME}\n"
        "  Traite automatiquement les catégories et intègre une validation croisée.\n\n"
        "  Code retour : 0 = succès, 1 = erreur."
    )

if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        _print_help()
        sys.exit(0)
    sys.exit(main())
