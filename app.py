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
from src.ui_components import render_global_reporter

st.set_page_config(
    page_title=APP_NAME,
    page_icon=app_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- SÉCURITÉ : AUTHENTIFICATION FIREBASE ---
from src.firebase_auth import init_auth
init_auth()

auth = st.session_state.firebase_auth

if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>Vision-Boot Login</h1>", unsafe_allow_html=True)
        
        if not auth.is_configured:
            st.info("💡 **Mode Démo Actif** : Aucune clé Firebase détectée. Vous pouvez vous connecter avec n'importe quel email/mot de passe pour tester.")
            
        tab_login, tab_register = st.tabs(["Connexion", "Inscription (Nouveau compte)"])
        
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="votre@email.com")
                password = st.text_input("Mot de passe", type="password")
                if st.form_submit_button("Se connecter", type="primary", use_container_width=True):
                    if not email or not password:
                        st.error("Veuillez remplir tous les champs.")
                    else:
                        user_info, error = auth.login(email, password)
                        if error:
                            st.error(error)
                        else:
                            st.session_state.user = user_info
                            st.rerun()
        
        with tab_register:
            with st.form("register_form"):
                reg_email = st.text_input("Email", placeholder="votre@email.com")
                reg_password = st.text_input("Mot de passe", type="password", help="Minimum 6 caractères")
                reg_name = st.text_input("Nom complet", placeholder="Jean Dupont")
                if st.form_submit_button("S'inscrire", use_container_width=True):
                    if not reg_email or not reg_password or not reg_name:
                        st.error("Veuillez remplir tous les champs.")
                    else:
                        user_info, error = auth.register(reg_email, reg_password, reg_name)
                        if error:
                            st.error(error)
                        else:
                            st.success("🎯 Compte créé avec succès ! Connectez-vous dès maintenant.")
    st.stop()

# Information utilisateur pour le reste de l'app
name = st.session_state.user.get("displayName", "Utilisateur")
email_user = st.session_state.user.get("email", "Non spécifié")

# Si authentifié, on affiche le bouton de déconnexion dans la sidebar plus bas
# -----------------------------------

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
from src.ui_components import render_vision_boot_bot, exportable_plot

def _show_gracious_error(error_msg: str):
    """Affiche une erreur pédagogique avec option de téléchargement du template CSV."""
    st.sidebar.error(error_msg)
    if "Colonnes manquantes" in error_msg or "format" in error_msg.lower():
        st.sidebar.info("💡 Besoin d'aide ? Téléchargez notre modèle de données ci-dessous pour corriger votre fichier.")
        template_bytes = proc.generate_csv_template()
        st.sidebar.download_button(
            label="📥 Télécharger le modèle CSV",
            data=template_bytes,
            file_name="modele_vision_boot.csv",
            mime="text/csv",
            key="btn_download_template"
        )


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


@st.cache_resource(show_spinner=False)
def get_vision_shop_db():
    from src.database_manager import DatabaseManager
    from config import VISION_SHOP_DB_PATH
    return DatabaseManager(VISION_SHOP_DB_PATH)

@st.cache_data(ttl=600)
def get_cached_all_data():
    """Récupère les données SQL de manière optimisée pour le dashboard."""
    db = get_vision_shop_db()
    return db.get_all_data()

def _check_and_show_data_warning() -> bool:
    """Vérifie si les données sont présentes. Si non, affiche un message mais ne bloque pas l'application."""
    if st.session_state["df_cleaned"] is None or not isinstance(st.session_state["df_cleaned"], pd.DataFrame):
        st.warning(
            "🧪 **Mode Découverte** : Aucune donnée e-commerce n'est actuellement injectée.\n\n"
            "Pour débloquer les analyses et prédictions, veuillez utiliser la section **'Injection de Données'** "
            "dans la barre latérale à gauche."
        )
        st.info("💡 Conseil : Vous pouvez charger le **'Fichier local'** pour tester l'application immédiatement.")
        return False
    return True


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
    from src.ui_components import render_vision_boot_bot
    model_engine = get_model_engine()
    render_vision_boot_bot(model_engine)

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

    if st.sidebar.button("Se déconnecter"):
        st.session_state.user = None
        st.rerun()
        
    if not auth.is_configured:
        st.sidebar.warning("⚠️ MODE DÉMO ACTIF")
        
    st.sidebar.markdown(f"Bienvenue, **{name}**")
    # Synchronisation de la navigation sidbebar avec le bouton Retour
    page_list = [
        APP_PAGE_DASHBOARD,
        APP_PAGE_QUALITY,
        APP_PAGE_ANALYTICS,
        APP_PAGE_VISION_SHOP_STOCK,
        APP_PAGE_VISION_SHOP_DASH,
        APP_PAGE_FORECAST,
        APP_PAGE_SQL_UNIVERSAL,
    ]
    try:
        prev_index = page_list.index(st.session_state["main_nav"])
    except ValueError:
        prev_index = 0

    page = st.sidebar.radio(
        " ",
        page_list,
        index=prev_index,
        key="main_nav",
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
                    _show_gracious_error(str(e))
                except Exception:
                    _show_gracious_error("Import impossible : vérifiez le format du fichier.")

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
                        _show_gracious_error(str(e))
                    except Exception:
                        _show_gracious_error("Import impossible : vérifiez le texte collé.")

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
                _show_gracious_error(str(e))
            except Exception:
                _show_gracious_error("Import impossible : vérifiez le fichier d'exemple.")

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
                    _show_gracious_error(str(e))
                except Exception:
                    _show_gracious_error(
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
                    _show_gracious_error(str(e))
                except Exception:
                    _show_gracious_error(
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
                _show_gracious_error(str(e))
            except Exception:
                _show_gracious_error("Échec API : URL, SSL, format JSON/CSV ou colonnes.")



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
        st.session_state["vision_boot_messages"] = []
        st.rerun()


    st.sidebar.divider()
    st.sidebar.caption(
        "Jeu de données chargé"
        if st.session_state.get("df_cleaned") is not None
        else "En attente d'injection de données"
    )
    if page == APP_PAGE_DASHBOARD:
        if _check_and_show_data_warning():
            # --- BADGE ENGINE v2.0 (PREMIUM) ---
            st.markdown(
                """
                <div style="background-color:#1e1e1e; padding:15px; border-radius:10px; border-left: 5px solid #00ffcc; margin-bottom: 25px;">
                    <h4 style="color:#00ffcc; margin:0;">🛡️ Vision-ShopFlow Engine v2.0</h4>
                    <p style="color:white; font-size:14px; margin:5px 0 0 0;">
                        <b>Confidentialité :</b> Traitement local (RAM/SQLite). <br>
                        <b>Adaptabilité :</b> Structure de données auto-générée (Plug & Play).
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            st.header(APP_PAGE_DASHBOARD)
            df = _get_df_cleaned()
            
            # --- SYSTÈME D'ALERTES (AUDIT REMEDIATION) ---
            if "Categorie_Produit" in df.columns:
                stock_summary = df.groupby("Categorie_Produit")["Quantite"].sum()
                alert_cats = stock_summary[stock_summary < 5].index.tolist()
                if alert_cats:
                    st.toast(f"🚨 Alerte Stock Bas : {', '.join(alert_cats)}", icon="⚠️")

            # --- AFFICHAGE DES MÉTRIQUES ---
            metrics = st.session_state.get("resultats_ml", {})
            render_dashboard_metrics(df, metrics)
            render_dashboard_plots(df)
            render_vision_boot_insights(df, metrics)
            
            # --- REPORTING PDF (FINAL ASSEMBLY) ---
            render_global_reporter(df)

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
            exportable_plot(fig, filename="dashboard_ca_categories")
            plt.close(fig)

    elif page == APP_PAGE_VISION_SHOP_STOCK:
        from src.ui_components import render_return_home_button

        render_return_home_button()
        st.header(APP_PAGE_VISION_SHOP_STOCK)
        st.caption(
            f"Vision-ShopFlow — base SQLite persistante : `{VISION_SHOP_DB_PATH.name}` "
            "(les données survivent aux redémarrages de l’application)."
        )
        db = get_vision_shop_db()
        with st.form("ajout_vente_sql"):
            st.subheader("Ajouter une transaction")
            prod = st.text_input("Nom du produit")
            prix = st.number_input("Prix unitaire (€)", min_value=0.0, format="%.2f")
            qte = st.number_input("Quantité", min_value=1, step=1)
            age = st.number_input("Âge client", min_value=15, max_value=120, value=35)
            submitted = st.form_submit_button("Enregistrer en base de données", type="primary")
        if submitted:
            if not (prod or "").strip():
                st.warning("Indiquez un nom de produit.")
            else:
                db.ajouter_vente(prod, prix, qte, age)
                st.success("Vente enregistrée avec succès.")
                st.rerun()

        data = db.get_all_data()
        st.subheader("Historique des ventes")
        if data.empty:
            st.info("Aucune vente en base — utilisez le formulaire ci-dessus.")
        else:
            st.dataframe(data, use_container_width=True)
            dc1, dc2 = st.columns([1, 2])
            with dc1:
                del_id = st.number_input(
                    "Supprimer la vente n°",
                    min_value=1,
                    step=1,
                    key="del_vente_id",
                )
            with dc2:
                st.write("")
                if st.button("Supprimer cette ligne", key="btn_del_vente"):
                    if db.supprimer_vente(int(del_id)):
                        st.success("Ligne supprimée.")
                        st.rerun()
                    else:
                        st.warning("Aucune vente avec cet identifiant.")

    elif page == APP_PAGE_VISION_SHOP_DASH:
        from src.ui_components import render_return_home_button
        from src.assistant_local import VisionBootLocal

        render_return_home_button()
        st.header(APP_PAGE_VISION_SHOP_DASH)
        db = get_vision_shop_db()
        raw = db.get_all_data()
        if raw.empty:
            st.warning(
                "La base de données est vide. Ajoutez des ventes dans l’onglet **Gestion du Stock**."
            )
        else:
            data = raw.copy()
            data["_montant"] = data["prix_unitaire"] * data["quantite"]
            ca_total = float(data["_montant"].sum())
            col1, col2, col3 = st.columns(3)
            col1.metric("Chiffre d’affaires", f"{ca_total:,.2f} €")
            col2.metric("Nombre de ventes", len(data))
            col3.metric("Références produit", int(data["produit"].nunique()))

            st.subheader("Quantités vendues par produit")
            q_par_p = data.groupby("produit", as_index=False)["quantite"].sum().sort_values(
                "quantite", ascending=False
            )
            st.bar_chart(q_par_p.set_index("produit"))

            df_vb = proc.dataframe_vision_shop_to_ecommerce(raw)
            if not df_vb.empty:
                st.subheader("Vision-Boot — diagnostic")
                vb = st.session_state.get("local_assistant") or VisionBootLocal()
                st.markdown(vb.get_smart_analysis(df_vb))

            st.divider()
            st.caption(
                "Synchronise le jeu issu de la base SQL avec le moteur global (tableau de bord, analyse, prédiction ML)."
            )
            if st.button(
                "Synchroniser avec Vision-Boot (session + archive)",
                type="primary",
                key="sync_sql_to_session",
            ):
                df_cleaned = proc.dataframe_vision_shop_to_ecommerce(raw)
                if len(df_cleaned) == 0:
                    st.warning("Données insuffisantes après normalisation.")
                else:
                    sig = hashlib.sha256(
                        raw.astype(str).to_csv(index=False).encode("utf-8")
                    ).hexdigest()
                    _finalize_clean_import(df_cleaned, str(VISION_SHOP_DB_PATH.name), sig)

    elif page == APP_PAGE_SQL_UNIVERSAL:
        from src.ui_components import render_return_home_button
        from src.ui_sql_universal import render_sql_universal_page

        render_return_home_button()
        st.header(APP_PAGE_SQL_UNIVERSAL)
        render_sql_universal_page()

    elif page == APP_PAGE_QUALITY:
        from src.ui_components import render_return_home_button
        render_return_home_button()
        
        st.header("📦 Gestion du Stock Dynamique")
        st.caption("Module Plug & Play : s'adapte automatiquement à votre format de données.")

        db = get_vision_shop_db()
        df_sql = db.get_table_data("stock_client")
        df_session = st.session_state.get("df_cleaned")

        if df_session is not None:
            # --- DÉTECTION DE CHANGEMENT DE SCHÉMA (UX PRO) ---
            cols_sql = set(df_sql.columns) if not df_sql.empty else set()
            cols_session = set(df_session.columns)
            
            if cols_sql and cols_sql != cols_session:
                st.warning("⚠️ **Structure Différente détectée** : Le fichier importé possède des colonnes différentes de votre stock actuel.")
                confirm = st.checkbox("J'accepte d'écraser la structure actuelle (Une sauvegarde sera créée en base).")
                if not confirm:
                    st.info("💡 Enregistrez d'abord une copie de vos données si nécessaire.")
                    st.stop()

            # --- GESTION HAUTE PERFORMANCE (PAGINATION) ---
            st.divider()
            n_rows = len(df_sql) if not df_sql.empty else 0
            st.write(f"Stock actuel : **{n_rows} lignes** indexées.")
            
            if n_rows > 100:
                st.info("⚡ Affichage optimisé : Seules les 100 dernières lignes sont éditables pour garantir la fluidité.")
                df_to_edit = df_sql.tail(100)
            else:
                df_to_edit = df_sql if not df_sql.empty else df_session

            edited_df = st.data_editor(
                df_to_edit, 
                num_rows="dynamic", 
                use_container_width=True,
                key="dynamic_stock_editor"
            )
            
            if st.button("💾 Synchroniser & Sauvegarder (v2.0)", type="primary"):
                with st.spinner("Migration et Indexation en cours..."):
                    from src.processor import validate_manual_entry
                    final_df = validate_manual_entry(edited_df)
                    
                    # Si c'était un nouvel import, on prend tout le df_session
                    if df_sql.empty or cols_sql != cols_session:
                        sync_res = db.sync_any_dataframe(df_session, "stock_client")
                    else:
                        # Sinon on merge les modifs de l'éditeur dans le df_sql (simplifié pour démo: on remplace)
                        sync_res = db.sync_any_dataframe(final_df, "stock_client")
                        
                    st.success(sync_res)
                    st.rerun()
        else:
            st.info("ℹ️ Veuillez injecter des données (CSV/SQL) pour commencer la gestion de stock.")

    elif page == APP_PAGE_ANALYTICS:
        from src.ui_components import render_return_home_button
        render_return_home_button()
        if _check_and_show_data_warning():
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
                from src.ui_components import render_vision_boot_insights
                render_vision_boot_insights(df_plot)
                
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
                    exportable_plot(fig1, filename=f"ca_categories_{cat_selected}")
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
                exportable_plot(fig2, filename=f"relation_prix_quantite_{cat_selected}")
                plt.close(fig2)

    elif page == APP_PAGE_FORECAST:
        from src.ui_components import render_return_home_button
        render_return_home_button()
        if _check_and_show_data_warning():
            st.header(APP_PAGE_FORECAST)

            model = get_model_engine()

            # --- GESTION PREMIUM DES VERSIONS (AUDIT v2.0) ---
            if model.version == "INCOMPATIBLE":
                st.warning("⚠️ **Vieux Cerveau Détecté** : La structure interne a évolué pour inclure les catégories (Audit v2.0).")
                st.info("Votre ancien modèle local n'est plus compatible. Veuillez le mettre à jour pour débloquer les nouvelles capacités.")
                if st.button("🚀 Mettre à jour en Version 2.0 (Premium)", type="primary"):
                    with st.spinner("Optimisation du cerveau IA..."):
                        model.auto_train(_get_df_cleaned())
                    st.success("Mise à jour réussie ! Vision-Boot est maintenant prêt.")
                    st.rerun()
                st.stop()

            if model.model is None:
                st.info("ℹ️ Aucun cerveau IA entraîné pour le moment.")
                if st.button("🚀 Entraîner Vision-Boot (Auto-ML)", type="primary"):
                    with st.spinner("Vision-Boot analyse et choisit le meilleur modèle..."):
                        model.auto_train(_get_df_cleaned())
                    st.success("Entraînement terminé !")
                    st.rerun()
            else:
                st.success(f"🤖 **Vision-Boot opérationnel** (Version {model.version})")
                st.caption(f"Dernière optimisation : {model.updated_at}")
                
                # --- AUTO-ML Section ---
                with st.expander("⚙️ Options d'entraînement", expanded=False):
                    if st.button("🔄 Ré-entraîner sur les données actuelles"):
                        with st.spinner("Rafraîchissement du modèle..."):
                            model.auto_train(_get_df_cleaned())
                        st.success("Cerveau rafraîchi.")
                        st.rerun()
                
                st.divider()
                st.subheader("🔮 Prédiction Interactive")
                col1, col2, col3 = st.columns(3)
                age = col1.number_input("Âge du Client", 18, 100, 35)
                qte = col2.number_input("Quantité estimée", 1, 50, 1)
                
                df = _get_df_cleaned()
                cats = sorted(df["Categorie_Produit"].unique().tolist()) if "Categorie_Produit" in df.columns else ["Divers"]
                cat_sel = col3.selectbox("Catégorie Produit", cats)

                if st.button("Calculer le Montant Estimé", type="primary", use_container_width=True):
                    pred = model.predict_amount(age, qte, cat_sel)
                    st.balloons()
                    st.markdown(
                        f"<div style='background-color: #1a1a1a; padding: 25px; border-radius: 10px; border-left: 5px solid #00ff00;'>"
                        f"<h2 style='color: white; margin:0;'>Vente Estimée : {pred:,.2f} €</h2>"
                        f"<p style='color: #888;'>Basé sur l'IA Vision-Boot (v{model.version}) pour le segment {cat_sel}.</p>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

    st.divider()
    st.caption(f"© {APP_NAME}")

