# Shopping Cart Graph — application Streamlit (données e-commerce).
# Démarrage à zéro : aucune donnée chargée automatiquement ; persistance via
# st.session_state (df_cleaned, historiques). Traçabilité disque : historique_traitements/.

import datetime
import hashlib
import io
import json
import os
import pickle
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

from config import *

st.set_page_config(
    page_title=APP_NAME,
    page_icon=app_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Forcer la langue HTML de base à "fr" pour éviter la traduction automatique par le navigateur
import streamlit.components.v1 as components
components.html(
    """
    <script>
        const html = window.parent.document.querySelector("html");
        if (html) html.lang = 'fr';
    </script>
    """,
    height=0,
    width=0,
)

from src.ui_components import init_session_state
init_session_state()
RESULTATS_ML_COLONNES = (
    "Horodatage",
    "Age_Client",
    "Quantite",
    "Montant_estime_EUR",
)

sns.set_style("whitegrid")
plt.rc("figure", figsize=(10, 6))


import src.processor as proc


def _enregistrer_traitement_session(
    df: pd.DataFrame, chemin_archive: Optional[Path], fichier_source: str
) -> None:
    hist = st.session_state["traitement_historique"]
    entree = {
        "horodatage": datetime.datetime.now().isoformat(timespec="seconds"),
        "chemin_disque": str(chemin_archive) if chemin_archive else None,
        "lignes": int(len(df)),
        "fichier_source": fichier_source,
    }
    hist.append(entree)
    del hist[: max(0, len(hist) - HISTORIQUE_MAX_ENTREES)]


def _finalize_clean_import(df_cleaned: pd.DataFrame, nom_source: str, signature: str) -> None:
    """Archive disque (df_ecommerce_nettoye.csv), historique session, mémoire session, rerun."""
    chemin_csv = proc._archiver_nettoyage_sur_disque(df_cleaned)
    if chemin_csv is None:
        st.sidebar.warning(
            "Archivage disque indisponible (droits, chemin ou espace). "
            "Les données restent chargées en session."
        )
    _enregistrer_traitement_session(df_cleaned, chemin_csv, nom_source)
    st.session_state["df_cleaned"] = df_cleaned  # persistance entre réexécutions Streamlit
    st.session_state["_upload_sig"] = signature
    st.session_state["import_ok"] = True
    st.rerun()


@st.cache_resource(show_spinner=False)
def get_model_engine():
    from src.model_manager import ModelManager
    from config import MODEL_PATH
    return ModelManager(MODEL_PATH)


def _require_data() -> None:
    """Barrière : aucune visualisation / prédiction sans jeu injecté."""
    if st.session_state["df_cleaned"] is None:
        st.warning(
            "⚠️ Sécurité : Veuillez d'abord injecter un fichier de données e-commerce valide via la barre latérale."
        )
        st.stop()
    if not isinstance(st.session_state["df_cleaned"], pd.DataFrame):
        st.session_state["df_cleaned"] = None
        st.warning(
            "⚠️ Sécurité : Veuillez d'abord injecter un fichier de données e-commerce valide via la barre latérale."
        )
        st.stop()


def _get_df_cleaned() -> pd.DataFrame:
    """DataFrame exploitable après _require_data() (évite NameError / état incohérent)."""
    df = st.session_state["df_cleaned"]
    if not isinstance(df, pd.DataFrame):
        st.session_state["df_cleaned"] = None
        st.warning(
            "⚠️ Sécurité : Veuillez d'abord injecter un fichier de données e-commerce valide via la barre latérale."
        )
        st.stop()
    return df



main_col, bot_col = st.columns([3, 1])

with bot_col:
    from src.ui_components import render_shoppy_bot
    model_engine = get_model_engine()
    render_shoppy_bot(model_engine)

with main_col:
    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        if os.path.exists(icon_path):
            st.image(icon_path, width=90)
    with col_title:
        st.title(APP_NAME)
        st.caption(APP_TAGLINE)
    if st.session_state.pop("import_ok", False):
        st.success("Données e-commerce injectées, nettoyées et mémorisées pour cette session.")

    st.divider()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        " ",
        [
            APP_PAGE_DASHBOARD,
            APP_PAGE_QUALITY,
            APP_PAGE_ANALYTICS,
            APP_PAGE_FORECAST,
        ],
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    st.sidebar.subheader("Injection de Données")

    _sample_path = SCRIPT_DIR / SAMPLE_CSV_NAME
    _inj_choices: list[tuple[str, str]] = [
        (INJ_LABEL_FILE, "file"),
        (INJ_LABEL_PASTE, "paste"),
    ]
    if _sample_path.is_file():
        _inj_choices.append((INJ_LABEL_SAMPLE, "sample"))
    _inj_choices.extend(
        [
            (INJ_LABEL_DB, "db"),
            (INJ_LABEL_API, "api"),
        ]
    )

    _inj_labels = [c[0] for c in _inj_choices]
    _inj_mode = st.sidebar.selectbox(
        "Type d'injection",
        _inj_labels,
        key="inj_mode_sb",
        help="CSV, collage, fichier local, base SQL (SQLite / SQLAlchemy) ou API HTTP GET (JSON ou CSV).",
    )
    _inj_code = dict(_inj_choices)[_inj_mode]

    if _inj_code == "file":
        _upload = st.sidebar.file_uploader(
            "Fichier CSV e-commerce",
            type=["csv"],
            key=f"fu_csv_{st.session_state['_uploader_key']}",
            help="Les données nettoyées sont conservées dans la session entre les interactions.",
        )
        if _upload is not None:
            raw = _upload.getvalue()
            sig = proc._upload_fingerprint(raw, _upload.name or "upload.csv")
            if sig != st.session_state.get("_upload_sig"):
                try:
                    df_in = proc._read_uploaded_csv_bytes(raw)
                    df_in.columns = df_in.columns.astype(str).str.strip()
                    df_cleaned = proc.prepare_ecommerce_dataframe(df_in)
                    if len(df_cleaned) == 0:
                        st.sidebar.error("Aucune ligne valide après préparation.")
                    else:
                        _finalize_clean_import(
                            df_cleaned, _upload.name or "upload.csv", sig
                        )
                except ValueError as e:
                    st.sidebar.error(str(e))
                except Exception:
                    st.sidebar.error("Import impossible : vérifiez le format du fichier.")

    elif _inj_code == "paste":
        _csv_text = st.sidebar.text_area(
            "Collez le CSV (ligne d'en-têtes + données)",
            height=160,
            key="csv_paste_ta",
            help="Séparateur virgule ou point-virgule. Colonnes requises : voir message d’erreur si incohérent.",
        )
        if st.sidebar.button("Importer ce texte", type="primary", key="btn_paste_csv"):
            if not (_csv_text or "").strip():
                st.sidebar.error("Collez d'abord un contenu CSV.")
            else:
                sig = hashlib.sha256(_csv_text.encode("utf-8")).hexdigest()
                if sig == st.session_state.get("_upload_sig"):
                    st.sidebar.info("Ce jeu est déjà chargé.")
                else:
                    try:
                        df_in = proc._read_csv_from_text(_csv_text)
                        df_in.columns = df_in.columns.astype(str).str.strip()
                        df_cleaned = proc.prepare_ecommerce_dataframe(df_in)
                        if len(df_cleaned) == 0:
                            st.sidebar.error("Aucune ligne valide après préparation.")
                        else:
                            _finalize_clean_import(df_cleaned, "collage_csv.txt", sig)
                    except ValueError as e:
                        st.sidebar.error(str(e))
                    except Exception:
                        st.sidebar.error("Import impossible : vérifiez le texte collé.")

    elif _inj_code == "sample":
        st.sidebar.caption(f"Source : `{SAMPLE_CSV_NAME}` à côté de l'application.")
        if st.sidebar.button("Charger ce fichier", type="primary", key="btn_sample_csv"):
            try:
                raw = _sample_path.read_bytes()
                sig = proc._upload_fingerprint(raw, SAMPLE_CSV_NAME)
                if sig == st.session_state.get("_upload_sig"):
                    st.sidebar.info("Ce fichier est déjà chargé.")
                else:
                    df_in = proc._read_uploaded_csv_bytes(raw)
                    df_in.columns = df_in.columns.astype(str).str.strip()
                    df_cleaned = proc.prepare_ecommerce_dataframe(df_in)
                    if len(df_cleaned) == 0:
                        st.sidebar.error("Aucune ligne valide après préparation.")
                    else:
                        _finalize_clean_import(df_cleaned, SAMPLE_CSV_NAME, sig)
            except OSError as e:
                st.sidebar.error(f"Lecture impossible : {e}")
            except ValueError as e:
                st.sidebar.error(str(e))
            except Exception:
                st.sidebar.error("Import impossible : vérifiez le fichier d'exemple.")

    elif _inj_code == "db":
        st.sidebar.caption(
            "La requête doit retourner les colonnes attendues (schéma e-commerce). "
            "SQLite : fichier local. SQLAlchemy : PostgreSQL, MySQL, MariaDB, etc."
        )
        _db_engine = st.sidebar.radio(
            "Type de connexion",
            ["SQLite (fichier .db)", "SQLAlchemy (URL)"],
            key="inj_db_engine",
        )
        _db_sql = st.sidebar.text_area(
            "Requête SQL",
            height=90,
            key="inj_db_sql",
            value="SELECT * FROM transactions LIMIT 5000",
        )
        if _db_engine.startswith("SQLite"):
            _sqlite_path = st.sidebar.text_input(
                "Chemin du fichier .db",
                key="inj_sqlite_path",
                placeholder=r"ex. C:\data\ventes.db ou .\boutique.sqlite",
            )
            if st.sidebar.button("Exécuter et importer", type="primary", key="btn_db_sqlite"):
                try:
                    df_in = proc._load_sqlite_dataframe(_sqlite_path, _db_sql)
                    df_in.columns = df_in.columns.astype(str).str.strip()
                    df_cleaned = proc.prepare_ecommerce_dataframe(df_in)
                    if len(df_cleaned) == 0:
                        st.sidebar.error("Aucune ligne valide après préparation.")
                    else:
                        sig = hashlib.sha256(
                            f"sqlite|{_sqlite_path}|{_db_sql}".encode("utf-8")
                        ).hexdigest()
                        if sig == st.session_state.get("_upload_sig"):
                            st.sidebar.info("Ce jeu est déjà chargé.")
                        else:
                            _label = f"sqlite:{Path(_sqlite_path.strip() or '.').name}"
                            _finalize_clean_import(df_cleaned, _label, sig)
                except ValueError as e:
                    st.sidebar.error(str(e))
                except Exception:
                    st.sidebar.error(
                        "Échec SQL : chemin .db, syntaxe SQL ou colonnes incompatibles."
                    )
        else:
            _sa_url = st.sidebar.text_input(
                "URL SQLAlchemy",
                key="inj_sa_url",
                placeholder="postgresql://user:mdp@localhost:5432/ma_base",
            )
            st.sidebar.caption(
                "Ex. `sqlite:///./data.db` · pour PostgreSQL : `pip install psycopg2-binary`"
            )
            if st.sidebar.button("Exécuter et importer", type="primary", key="btn_db_sa"):
                try:
                    df_in = proc._load_sqlalchemy_dataframe(_sa_url, _db_sql)
                    df_in.columns = df_in.columns.astype(str).str.strip()
                    df_cleaned = proc.prepare_ecommerce_dataframe(df_in)
                    if len(df_cleaned) == 0:
                        st.sidebar.error("Aucune ligne valide après préparation.")
                    else:
                        sig = hashlib.sha256(
                            f"sa|{_sa_url}|{_db_sql}".encode("utf-8")
                        ).hexdigest()
                        if sig == st.session_state.get("_upload_sig"):
                            st.sidebar.info("Ce jeu est déjà chargé.")
                        else:
                            _finalize_clean_import(df_cleaned, "sqlalchemy", sig)
                except ValueError as e:
                    st.sidebar.error(str(e))
                except Exception:
                    st.sidebar.error(
                        "Échec SQLAlchemy : URL, pilote Python (psycopg2, pymysql…), requête ou colonnes."
                    )

    elif _inj_code == "api":
        st.sidebar.caption(
            "Requête **GET** uniquement. Réponse : JSON (liste ou {data|results|records|items|ventes}) "
            "ou texte **CSV**."
        )
        _api_url = st.sidebar.text_input(
            "URL de l'API",
            key="inj_api_url",
            placeholder="https://exemple.com/api/ventes",
        )
        _api_headers = st.sidebar.text_area(
            "En-têtes HTTP (optionnel)",
            height=72,
            key="inj_api_headers",
            placeholder="Authorization: Bearer votre_jeton",
        )
        if st.sidebar.button("Charger depuis l'API", type="primary", key="btn_api_fetch"):
            try:
                df_in = proc._fetch_url_dataframe(_api_url, _api_headers)
                df_in.columns = df_in.columns.astype(str).str.strip()
                _sig_payload = (
                    (_api_url or "").encode("utf-8")
                    + b"\n"
                    + df_in.astype(str).to_csv(index=False).encode("utf-8")[:12000]
                )
                sig = hashlib.sha256(_sig_payload).hexdigest()
                if sig == st.session_state.get("_upload_sig"):
                    st.sidebar.info("Ce jeu est déjà chargé.")
                else:
                    df_cleaned = proc.prepare_ecommerce_dataframe(df_in)
                    if len(df_cleaned) == 0:
                        st.sidebar.error("Aucune ligne valide après préparation.")
                    else:
                        _finalize_clean_import(df_cleaned, f"api:{_api_url[:80]}", sig)
            except ValueError as e:
                st.sidebar.error(str(e))
            except Exception:
                st.sidebar.error("Échec API : URL, SSL, format JSON/CSV ou colonnes.")



    _hist = st.session_state.get("traitement_historique") or []
    if _hist:
        with st.sidebar.expander("Historique des traitements (session)", expanded=False):
            for h in reversed(_hist[-8:]):
                st.caption(
                    f"{h.get('horodatage', '—')} · {h.get('lignes', '?')} lignes · "
                    f"{h.get('fichier_source', '')}"
                )
                p = h.get("chemin_disque")
                if p:
                    st.caption(p)

    if st.sidebar.button("Réinitialiser les données", key="btn_reset"):
        st.session_state["df_cleaned"] = None
        st.session_state["_upload_sig"] = None
        st.session_state["_uploader_key"] = int(st.session_state["_uploader_key"]) + 1
        st.session_state["resultats_ml"] = []
        st.session_state["shoppy_messages"] = []
        st.rerun()


    st.sidebar.divider()
    st.sidebar.caption(
        "Jeu de données chargé"
        if st.session_state.get("df_cleaned") is not None
        else "En attente d'injection de données"
    )

    if page == APP_PAGE_DASHBOARD:
        _require_data()
        st.header(APP_PAGE_DASHBOARD)
        df = _get_df_cleaned()
        total_ca = float(df["Montant_Total"].sum())
        n = len(df)
        panier_moyen = total_ca / n if n else 0.0
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Transactions", f"{n:,}".replace(",", " "))
        c2.metric("Chiffre d’affaires (€)", f"{total_ca:,.0f}")
        c3.metric("Panier moyen (€)", f"{panier_moyen:,.2f}")
        c4.metric("Catégories actives", df["Categorie_Produit"].nunique())

        st.subheader("Répartition du CA par catégorie")
        ca_par_cat = (
            df.groupby("Categorie_Produit")["Montant_Total"]
            .sum()
            .sort_values(ascending=True)
        )
        fig, ax = plt.subplots(figsize=(10, max(4, 0.35 * len(ca_par_cat))))
        if len(ca_par_cat) > 0:
            colors = sns.color_palette("viridis", n_colors=len(ca_par_cat))
            ax.barh(np.arange(len(ca_par_cat)), ca_par_cat.values, color=colors)
            ax.set_yticks(np.arange(len(ca_par_cat)))
            ax.set_yticklabels(ca_par_cat.index)
        ax.set_xlabel("€")
        ax.set_title("CA par catégorie")
        st.pyplot(fig)
        plt.close(fig)

    elif page == APP_PAGE_QUALITY:
        _require_data()
        st.header(APP_PAGE_QUALITY)
        df = _get_df_cleaned()
        st.dataframe(df.head(15), use_container_width=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Lignes", len(df))
        m2.metric("Catégories", df["Categorie_Produit"].nunique())
        m3.metric("Montant total (€)", f"{df['Montant_Total'].sum():,.0f}")
        st.dataframe(df.describe(), use_container_width=True)

    elif page == APP_PAGE_ANALYTICS:
        _require_data()
        st.header(APP_PAGE_ANALYTICS)
        df_viz = _get_df_cleaned()

        categories = ["Toutes les catégories"] + list(df_viz["Categorie_Produit"].unique())
        cat_selected = st.selectbox("Catégorie", categories)

        if cat_selected != "Toutes les catégories":
            df_plot = df_viz[df_viz["Categorie_Produit"] == cat_selected]
        else:
            df_plot = df_viz

        st.metric("Transactions", len(df_plot))

        if df_plot.empty:
            st.warning("Aucune donnée pour ce filtre.")
        else:
            st.subheader("Chiffre d’affaires par catégorie")
            col_chart1, col_info1 = st.columns([2, 1])
            ca_par_cat = (
                df_plot.groupby("Categorie_Produit")["Montant_Total"]
                .sum()
                .sort_values(ascending=False)
            )

            with col_chart1:
                fig1, ax1 = plt.subplots()
                n_bars = len(ca_par_cat)
                if n_bars > 0:
                    x_pos = np.arange(n_bars)
                    colors = sns.color_palette("viridis", n_colors=n_bars)
                    ax1.bar(x_pos, ca_par_cat.values, color=colors, edgecolor="black")
                    ax1.set_xticks(x_pos)
                    ax1.set_xticklabels(ca_par_cat.index, rotation=45, ha="right")
                ax1.set_title("CA par catégorie (€)")
                ax1.set_ylabel("€")
                st.pyplot(fig1)
                plt.close(fig1)

            with col_info1:
                if not ca_par_cat.empty:
                    st.metric("Catégorie principale", str(ca_par_cat.index[0]))
                    st.metric("CA cumulé", f"{ca_par_cat.values[0]:,.0f} €")

            st.subheader("Prix × quantité")
            fig2, ax2 = plt.subplots()
            sns.scatterplot(
                data=df_plot,
                x="Prix_Unitaire",
                y="Quantite",
                hue="Categorie_Produit",
                alpha=0.6,
                ax=ax2,
                edgecolor="black",
                s=80,
            )
            ax2.set_title("Prix unitaire × quantité")
            ax2.grid(True, linestyle="--", alpha=0.5)
            st.pyplot(fig2)
            plt.close(fig2)

    elif page == APP_PAGE_FORECAST:
        _require_data()
        st.header(APP_PAGE_FORECAST)

        model = get_model_engine()
        if model.model is None:
            st.error(
                f"Modèle indisponible. Fichier « {MODEL_FILENAME} » requis à côté de l’application."
            )
            st.stop()

        df = _get_df_cleaned()
        if len(df) < 1:
            st.error("Données insuffisantes.")
            st.stop()

        # Entrées Scikit-learn : défauts explicites avant les widgets (cycle de vie Streamlit)
        age_input = 35
        quantite_input = 2
        try:
            age_input = int(st.session_state["age_input"])
            quantite_input = int(st.session_state["quantite_input"])
        except (KeyError, TypeError, ValueError):
            st.session_state["age_input"] = age_input
            st.session_state["quantite_input"] = quantite_input

        st.subheader("Estimation du montant")
        with st.form("form_prediction"):
            c1, c2 = st.columns(2)
            with c1:
                age_input = st.number_input(
                    "Âge client",
                    min_value=18,
                    max_value=100,
                    value=age_input,
                    step=1,
                )
            with c2:
                quantite_input = st.number_input(
                    "Quantité",
                    min_value=1,
                    max_value=20,
                    value=quantite_input,
                    step=1,
                )
            submit = st.form_submit_button("Estimer")

        if submit:
            st.session_state["age_input"] = int(age_input)
            st.session_state["quantite_input"] = int(quantite_input)
            input_data = pd.DataFrame(
                {
                    MODEL_FEATURES[0]: [st.session_state["age_input"]],
                    MODEL_FEATURES[1]: [st.session_state["quantite_input"]],
                }
            )
            try:
                raw_pred = model.predict_amount(st.session_state["age_input"], st.session_state["quantite_input"])
                prediction = max(0.0, raw_pred)
                st.success(f"**{prediction:,.2f} €**")
                _hist_ml = st.session_state["resultats_ml"]
                _hist_ml.append(
                    {
                        "Horodatage": datetime.datetime.now().isoformat(timespec="seconds"),
                        "Age_Client": int(st.session_state["age_input"]),
                        "Quantite": int(st.session_state["quantite_input"]),
                        "Montant_estime_EUR": round(float(prediction), 2),
                    }
                )
                del _hist_ml[: max(0, len(_hist_ml) - 500)]
            except Exception:
                st.error("Calcul impossible.")

    st.divider()
    st.caption(f"© {APP_NAME}")

