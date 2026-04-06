"""Interface SaaS : connexion URI client, choix de table, CRUD DataFrame, scan Vision-Boot."""

from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from config import SCRIPT_DIR, VISION_SHOP_DB_PATH


def _ensure_sql_session_keys() -> None:
    st.session_state.setdefault("sql_client_uri", None)
    st.session_state.setdefault("sql_client_schema", None)
    st.session_state.setdefault("_sql_uri_active", None)


def _get_vision_database():
    uri = (st.session_state.get("sql_client_uri") or "").strip()
    if not uri:
        return None
    if st.session_state.get("_sql_uri_active") != uri:
        from src.vision_database import VisionDatabase

        st.session_state["vision_db_client"] = VisionDatabase(uri)
        st.session_state["_sql_uri_active"] = uri
    return st.session_state.get("vision_db_client")


def render_sql_universal_page() -> None:
    _ensure_sql_session_keys()
    st.caption(
        "URI SQLAlchemy : `sqlite:///…`, `postgresql+psycopg2://…`, `mysql+pymysql://…`, "
        "`mssql+pyodbc://…`, etc. Les identifiants restent dans la session navigateur uniquement."
    )

    default_sqlite = f"sqlite:///{VISION_SHOP_DB_PATH.resolve().as_posix()}"
    col_a, col_b = st.columns([3, 1])
    with col_b:
        mask_uri = st.toggle("Masquer l’URI", value=False)
    with col_a:
        active_uri = st.text_input(
            "Chaîne de connexion (URI)",
            value=st.session_state.get("sql_client_uri") or default_sqlite,
            type="password" if mask_uri else "default",
            key="sql_uri_combined",
            help="Exemple SQLite local : " + default_sqlite,
        ).strip()

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Se connecter", type="primary", key="btn_sql_connect"):
            if not active_uri:
                st.warning("Indiquez une URI.")
            else:
                from src.vision_database import VisionDatabase

                v = VisionDatabase(active_uri)
                ok, msg = v.tester_connexion()
                if ok:
                    st.session_state["sql_client_uri"] = active_uri
                    st.session_state["_sql_uri_active"] = None
                    st.session_state["sql_client_schema"] = None
                    st.success(msg)
                    st.rerun()
                else:
                    st.warning(f"Échec : {msg}")
    with c2:
        if st.button("Déconnecter", key="btn_sql_disconnect"):
            st.session_state["sql_client_uri"] = None
            st.session_state["_sql_uri_active"] = None
            st.session_state.pop("vision_db_client", None)
            st.session_state["sql_client_schema"] = None
            st.info("Session SQL réinitialisée.")
            st.rerun()
    with c3:
        st.caption(f"Répertoire app : `{SCRIPT_DIR}`")

    vdb = _get_vision_database()
    if vdb is None:
        st.info("Connectez-vous pour lister les tables et éditer les données.")
        return

    schemas = vdb.lister_schemas()
    schema_sel: str | None = None
    if len(schemas) > 1:
        none_default = "(schéma par défaut)"
        opts = [none_default] + [s for s in schemas if s not in ("pg_catalog", "pg_toast")]
        sch = st.selectbox("Schéma (PostgreSQL / multi-schémas)", opts, key="sql_schema_pick")
        schema_sel = None if sch == none_default else sch
        st.session_state["sql_client_schema"] = schema_sel
    else:
        schema_sel = None

    tables = vdb.lister_tables(schema=schema_sel)
    if not tables:
        st.warning("Aucune table listée (droits, schéma ou base vide).")
        return

    selected = st.selectbox("Table à gérer", tables, key="sql_table_pick")
    max_rows = st.number_input(
        "Ligne max chargées (aperçu)",
        min_value=100,
        max_value=500_000,
        value=10_000,
        step=500,
        key="sql_max_rows",
    )

    try:
        df = vdb.lire_table(selected, schema=schema_sel, max_rows=int(max_rows))
    except Exception as e:
        st.warning(f"Lecture impossible : {e}")
        return

    st.markdown(f"#### Données : `{selected}`")
    st.caption(
        "L’enregistrement remplace le contenu de la table côté SQL (`if_exists='replace'`). "
        "À réserver aux environnements de test ou après sauvegarde."
    )

    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="sql_data_editor")

    if st.button("Enregistrer les modifications en base", type="primary", key="btn_sql_save"):
        try:
            vdb.ecrire_dataframe(selected, edited, if_exists="replace", schema=schema_sel)
            st.success("Table mise à jour.")
            st.rerun()
        except Exception as e:
            st.warning(f"Échec d’écriture : {e}")

    local = st.session_state.get("local_assistant")
    if local is None:
        from src.assistant_local import VisionBootLocal

        local = VisionBootLocal()
    st.markdown(local.get_smart_table_scan(edited))

    st.divider()
    st.markdown("##### Synchronisation Vision-Boot (module e-commerce)")
    st.caption(
        "Si les colonnes correspondent au schéma Vision-Boot, vous pouvez pousser cet aperçu "
        "vers le tableau de bord et le ML."
    )
    if st.button("Tenter la synchronisation schéma e-commerce", key="btn_sql_sync_ecom"):
        import src.processor as proc

        try:
            df_try = proc.prepare_ecommerce_dataframe(edited.copy())
            if len(df_try) == 0:
                st.warning("Après normalisation : aucune ligne valide.")
            else:
                sig = hashlib.sha256(
                    edited.astype(str).to_csv(index=False).encode("utf-8")
                ).hexdigest()
                st.session_state["df_cleaned"] = df_try
                st.session_state["_upload_sig"] = sig
                st.session_state["import_ok"] = True
                st.success("Jeu synchronisé avec la session Vision-Boot.")
                st.rerun()
        except Exception as e:
            st.info(
                "Cette table ne correspond pas au schéma e-commerce attendu "
                f"(import CSV classique toujours disponible). Détail : {e}"
            )

    with st.expander("Console SQL (requêtes manuelles)", expanded=False):
        st.warning("N’exécutez que des requêtes de confiance (risque d’injection / destruction).")
        raw_sql = st.text_area("SQL", height=120, key="sql_adhoc")
        if st.button("Exécuter", key="btn_sql_exec"):
            if not (raw_sql or "").strip():
                st.warning("Saisissez une requête.")
            else:
                try:
                    vdb.executer_commande(raw_sql.strip())
                    st.success("Requête exécutée.")
                    st.rerun()
                except Exception as e:
                    st.warning(str(e))
