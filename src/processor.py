import datetime
import hashlib
import io
import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    HISTORIQUE_ROOT,
    HISTORIQUE_CSV_NAME,
    REQUIRED_COLS,
    NUMERIC_PREP_COLS,
)

def _upload_fingerprint(raw: bytes, filename: str) -> str:
    h = hashlib.sha256()
    h.update(filename.encode("utf-8", errors="replace"))
    h.update(str(len(raw)).encode("ascii"))
    h.update(raw[:8192])
    if len(raw) > 16384:
        h.update(raw[-8192:])
    return h.hexdigest()

def _read_uploaded_csv_bytes(raw: bytes) -> pd.DataFrame:
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
            return df
    if last_err:
        raise last_err
    raise ValueError("Impossible de lire le fichier CSV.")

def _read_csv_from_text(text: str) -> pd.DataFrame:
    text = text.strip()
    if not text:
        raise ValueError("Texte vide.")
    last_err: Optional[Exception] = None
    for sep in (",", ";"):
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep)
        except Exception as e:
            last_err = e
            continue
        if len(df.columns) < 2 and len(df) > 0:
            continue
        return df
    if last_err:
        raise last_err
    raise ValueError("Impossible de lire le CSV collé.")

def _dataframe_from_api_body(body: bytes, content_type: str) -> pd.DataFrame:
    text = body.decode("utf-8-sig", errors="replace").strip()
    if not text:
        raise ValueError("Réponse vide.")
    ct = (content_type or "").lower()
    looks_json = "json" in ct or text[:1] in ("{", "[")
    if looks_json:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON invalide : {e}") from e
        if isinstance(data, list):
            return pd.json_normalize(data)
        if isinstance(data, dict):
            for key in ("data", "results", "records", "items", "ventes"):
                if key in data and isinstance(data[key], list):
                    return pd.json_normalize(data[key])
            return pd.json_normalize([data])
        raise ValueError("Format JSON non reconnu (attendu : tableau ou objet avec clé data/results).")
    return _read_csv_from_text(text)

def _fetch_url_dataframe(url: str, header_lines: str) -> pd.DataFrame:
    url = (url or "").strip()
    if not url:
        raise ValueError("URL vide.")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ShoppingCartGraph/1.0 (Streamlit)"},
        method="GET",
    )
    for line in (header_lines or "").strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            req.add_header(k.strip(), v.strip())
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raise ValueError(f"HTTP {e.code} : {e.reason}") from e
    except urllib.error.URLError as e:
        raise ValueError(f"URL inaccessible : {e.reason}") from e
    return _dataframe_from_api_body(body, ctype)

def _load_sqlite_dataframe(db_path: str, sql: str) -> pd.DataFrame:
    sql = (sql or "").strip()
    if not sql:
        raise ValueError("Requête SQL vide.")
    path = Path(db_path.strip()).expanduser()
    if not path.is_file():
        raise ValueError(f"Fichier SQLite introuvable : {path}")
    with sqlite3.connect(str(path)) as conn:
        return pd.read_sql_query(sql, conn)

def _load_sqlalchemy_dataframe(url: str, sql: str) -> pd.DataFrame:
    sql = (sql or "").strip()
    if not sql:
        raise ValueError("Requête SQL vide.")
    u = (url or "").strip()
    if not u:
        raise ValueError("URL SQLAlchemy vide.")
    try:
        from sqlalchemy import create_engine, text
    except ImportError as e:
        raise ValueError(
            "Installez sqlalchemy : pip install sqlalchemy "
            "(et le pilote de votre SGBD, ex. psycopg2-binary)."
        ) from e
    engine = create_engine(u, pool_pre_ping=True)
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn)

def prepare_ecommerce_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = out.columns.astype(str).str.strip()

    missing = REQUIRED_COLS - set(out.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes : {sorted(missing)}")

    for col in NUMERIC_PREP_COLS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.drop_duplicates()
    out = out.dropna(subset=sorted(REQUIRED_COLS))

    if "Montant_Total" not in out.columns:
        out["Montant_Total"] = out["Prix_Unitaire"] * out["Quantite"]

    mask = np.isfinite(out["Montant_Total"].to_numpy(dtype=float))
    out = out.loc[mask].reset_index(drop=True)

    if len(out) > 0:
        try:
            out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
            bad_dates = out["Date"].isna()
            if bad_dates.any():
                out = out.loc[~bad_dates].reset_index(drop=True)
        except Exception:
            pass

    return out


def dataframe_vision_shop_to_ecommerce(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Convertit les lignes de la table SQL `ventes` (Vision-Shop) vers le schéma
    `prepare_ecommerce_dataframe` pour Tableau de bord, Analyse et Vision-Boot.
    """
    if raw is None or raw.empty:
        return pd.DataFrame()
    rows = []
    for _, r in raw.iterrows():
        pid = int(r["id"])
        rows.append(
            {
                "ID_Transaction": f"VS-{pid}",
                "Date": r["date_vente"],
                "Categorie_Produit": str(r["produit"]).strip() or "Divers",
                "Prix_Unitaire": float(r["prix_unitaire"]),
                "Quantite": int(r["quantite"]),
                "Âge_Client": int(r["age_client"]),
                "Méthode_Paiement": "Carte",
                "Satisfaction_Client (1-5)": 4,
            }
        )
    df = pd.DataFrame(rows)
    return prepare_ecommerce_dataframe(df)


def _archiver_nettoyage_sur_disque(df: pd.DataFrame) -> Optional[Path]:
    try:
        now = datetime.datetime.now()
        dest_dir = HISTORIQUE_ROOT / now.strftime("%Y-%m-%d_%H-%M")
        if dest_dir.exists():
            dest_dir = HISTORIQUE_ROOT / now.strftime("%Y-%m-%d_%H-%M-%S")
        os.makedirs(dest_dir, exist_ok=True)
        out_path = dest_dir / HISTORIQUE_CSV_NAME
        export = df.copy()
        if "Date" in export.columns and pd.api.types.is_datetime64_any_dtype(export["Date"]):
            export["Date"] = export["Date"].dt.strftime("%Y-%m-%d %H:%M:%S")
        export.to_csv(out_path, index=False, encoding="utf-8-sig")
        return out_path
    except OSError:
        return None

def generate_csv_template() -> bytes:
    """Crée un fichier CSV factice avec les colonnes requises pour guider l'utilisateur."""
    from config import REQUIRED_COLS
    # On crée quelques données d'exemple pour le template
    example_data = {col: ["Exemple"] for col in REQUIRED_COLS}
    template_df = pd.DataFrame(example_data)
    
    output = io.BytesIO()
    # Utilisation de utf-8-sig pour la compatibilité Excel immédiate
    template_df.to_csv(output, index=False, encoding="utf-8-sig")
    return output.getvalue()

def validate_manual_entry(df: pd.DataFrame) -> pd.DataFrame:
    """Valide et nettoie un DataFrame de manière intelligente, même si les colonnes sont dynamiques."""
    # Coercition robuste pour toutes les colonnes numériques détectées
    for col in df.columns:
        if "prix" in col.lower() or "montant" in col.lower() or "cost" in col.lower():
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).clip(lower=0)
        elif "quantite" in col.lower() or "stock" in col.lower() or "qte" in col.lower() or "age" in col.lower():
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int).clip(lower=0)
    
    # Recalcul spécifique e-commerce si les colonnes standards existent
    if "Prix_Unitaire" in df.columns and "Quantite" in df.columns:
        df["Montant_Total"] = df["Prix_Unitaire"] * df["Quantite"]
    
    return df

def clean_dynamic_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyage universel v2 : transforme n'importe quel CSV client en base SQL propre."""
    # Suppression des lignes vides
    df = df.dropna(how="all")
    
    # Nettoyage des noms de colonnes (pas d'espaces bizarres)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Coercition automatique : si une colonne contient +80% de nombres, on force le type
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notnull().mean() > 0.8:
            df[col] = converted.fillna(0.0)
            
    return df
