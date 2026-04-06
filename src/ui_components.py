import streamlit as st
import datetime
from config import MODEL_FEATURES
from src.assistant_local import VisionBootLocal
from src.reporter import generate_full_pdf_report

def init_session_state() -> None:
    """Initialisation session : df_cleaned = None tant qu'aucune injection."""
    if "df_cleaned" not in st.session_state:
        st.session_state["df_cleaned"] = None
    st.session_state.setdefault("_upload_sig", None)
    st.session_state.setdefault("_uploader_key", 0)
    st.session_state.setdefault("age_input", 35)
    st.session_state.setdefault("quantite_input", 2)
    st.session_state.setdefault("traitement_historique", [])
    st.session_state.setdefault("resultats_ml", [])
    st.session_state.setdefault("vision_boot_messages", [])
    st.session_state.setdefault("vision_boot_active", False)
    st.session_state.setdefault("main_nav", "Tableau de bord")
    st.session_state.setdefault("sql_client_uri", None)
    st.session_state.setdefault("sql_client_schema", None)
    if "local_assistant" not in st.session_state:
        st.session_state["local_assistant"] = VisionBootLocal()


def render_vision_boot_bot(model_engine=None):
    """Panneau Vision-Boot : moteur heuristique intégré, aucune configuration."""
    local = st.session_state["local_assistant"]

    if "vision_boot_active" not in st.session_state:
        st.session_state["vision_boot_active"] = True

    is_open = st.session_state["vision_boot_active"]
    drawer_right = "0" if is_open else "-400px"
    main_padding = "380px" if is_open else "0"

    st.markdown(
        f"""
        <style>
        div[data-testid="stHorizontalBlock"]:has(.assistant-anchor) > div:nth-child(1) {{
            transition: padding-right 0.3s ease-in-out !important;
            padding-right: {main_padding} !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.assistant-anchor) > div:nth-child(2) {{
            position: fixed !important;
            right: {drawer_right} !important;
            top: 0 !important;
            width: 380px !important;
            height: 100vh !important;
            background-color: #1a1c24 !important;
            z-index: 999999 !important;
            padding: 3.5rem 1rem 1rem 1rem !important;
            border-left: 1px solid rgba(255, 255, 255, 0.1) !important;
            transition: right 0.3s ease-in-out !important;
            box-shadow: -10px 0 30px rgba(0,0,0,0.5) !important;
            display: flex !important;
            flex-direction: column !important;
            overflow-y: auto !important;
        }}
        </style>
        <div class="assistant-anchor"></div>
        """,
        unsafe_allow_html=True,
    )

    sidebar_container = st.sidebar.container()
    with sidebar_container:
        st.markdown("##### 🤖 Vision-Boot")
        btn_label = "❌ Fermer le panneau" if is_open else "✨ Ouvrir Vision-Boot"
        if st.button(
            btn_label,
            use_container_width=True,
            type="primary" if not is_open else "secondary",
            key="toggle_bot_main",
        ):
            st.session_state["vision_boot_active"] = not is_open
            st.rerun()

        if st.session_state.get("df_cleaned") is not None:
            if st.button("✨ Lancer Vision-Boot", use_container_width=True, type="primary", key="btn_vision_analyze"):
                with st.status("Vision-Boot scanne vos ventes..."):
                    rapport = local.get_smart_analysis(st.session_state["df_cleaned"])
                st.session_state["vision_boot_messages"].append(
                    {"role": "assistant", "content": rapport}
                )
                st.session_state["vision_boot_active"] = True
                st.rerun()
        else:
            st.caption("Chargez des données pour activer l’analyse Vision-Boot.")

    st.markdown("---")
    with st.form(key="vision_chat_form", clear_on_submit=True):
        st.write("**Posez une question sur vos ventes :**")
        col_inp, col_btn = st.columns([3, 1])
        with col_inp:
            user_input = st.text_input(
                "Message",
                label_visibility="collapsed",
                placeholder="Ex. : Comment se porte mon activité ?",
            )
        with col_btn:
            submit_clicked = st.form_submit_button("Envoyer", use_container_width=True)

    if submit_clicked and user_input:
        st.session_state["vision_boot_messages"].append({"role": "user", "content": user_input.strip()})

    st.markdown("---")
    chat_container = st.container(height=550, border=False)

    with chat_container:
        if not st.session_state["vision_boot_messages"]:
            st.markdown(
                """
                <div style='background-color: rgba(46, 204, 113, 0.05); padding: 15px; border-radius: 10px;'>
                    <strong style="color: #2ecc71;">Hello ! Je suis Vision-Boot.</strong><br>
                    Je suis disponible pour vous aider, posez votre question ci-dessus.<br>
                    <strong>Vision-Boot 2.0</strong> : Moteur d’analyse heuristique intégré — instantané et sans configuration.<br>
                    Utilisez <strong>Lancer Vision-Boot</strong> ou posez une question ci-dessus.
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Guide de démarrage (Onboarding)
        if not st.session_state.get("df_cleaned") is not None:
            with st.expander("🚀 Guide de démarrage rapide", expanded=True):
                st.markdown("""
                1. **Injection** : Téléchargez un CSV ou connectez-vous à une base.
                2. **Synchronisation** : Cliquez sur 'Lancer Vision-Boot'.
                3. **Décision** : Utilisez les insights IA et les rapports PDF pour piloter votre activité.
                """)

        for msg in st.session_state["vision_boot_messages"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if st.session_state["vision_boot_messages"] and st.session_state["vision_boot_messages"][-1]["role"] == "user":
        with chat_container:
            with st.chat_message("assistant"):
                placeholder = st.empty()
                df = st.session_state.get("df_cleaned")
                with st.status("Vision-Boot prépare votre réponse..."):
                    full_response = local.get_smart_analysis(df)
                placeholder.markdown(full_response)

        st.session_state["vision_boot_messages"].append({"role": "assistant", "content": full_response})
        st.rerun()


def render_return_home_button():
    """Affiche un bouton pour revenir rapidement au tableau de bord."""
    if st.button("⬅️ Retour au Tableau de Bord"):
        st.session_state["main_nav"] = "Tableau de bord"
        st.rerun()


def render_vision_boot_insights(df, model_metrics=None):
    """Génère des conseils stratégiques automatiques (Moteur Vision-Boot)."""
    st.markdown("### 🤖 Analyse Stratégique : Vision-Boot")

    corr = df[["Âge_Client", "Montant_Total"]].corr().iloc[0, 1]

    best_cat = df.groupby("Categorie_Produit")["Montant_Total"].sum().idxmax()

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            """
        <div style="background-color: rgba(46, 204, 113, 0.1); border-left: 5px solid #2ecc71; padding: 15px; border-radius: 5px;">
            <strong style="color: #2ecc71;">🚀 OPPORTUNITÉ</strong><br>
            La catégorie <strong>{cat}</strong> génère le plus gros revenu. Concentrez vos stocks sur ce segment.
        </div>
        """.format(cat=best_cat),
            unsafe_allow_html=True,
        )

    with c2:
        if abs(corr) > 0.1:
            st.markdown(
                """
            <div style="background-color: rgba(52, 152, 219, 0.1); border-left: 5px solid #3498db; padding: 15px; border-radius: 5px;">
                <strong style="color: #3498db;">💡 INSIGHT CLIENT</strong><br>
                L'âge influence le panier moyen ({val:.2f}). Adaptez votre marketing par tranche d'âge.
            </div>
            """.format(val=corr),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
            <div style="background-color: rgba(241, 196, 15, 0.1); border-left: 5px solid #f1c40f; padding: 15px; border-radius: 5px;">
                <strong style="color: #f1c40f;">⚠️ ALERTE STABILITÉ</strong><br>
                Les achats sont homogènes. Pas de segment d'âge privilégié détecté pour l'instant.
            </div>
            """,
                unsafe_allow_html=True,
            )

    if model_metrics and model_metrics.get("best_algo") != "N/A":
        st.info(
            f"🧠 **Note de Vision-Boot** : J'ai sélectionné le modèle **{model_metrics['best_algo']}** "
            f"car il offre la meilleure précision ($R^2$ = {model_metrics['r2']:.4f})."
        )

        if "store_profile" in model_metrics:
            st.divider()
            col_prof1, col_prof2 = st.columns([1, 2])
            with col_prof1:
                st.write(f"🏷️ **Profil boutique :** {model_metrics['store_profile']}")
            with col_prof2:
                st.success(f"🎯 **Stratégie conseillée :** {model_metrics['strategy']}")

def render_global_reporter(df):
    """Bouton de génération de rapport PDF global."""
    st.divider()
    st.subheader("📄 Reporting Professionnel")
    if st.button("Générer le Rapport PDF Complet", type="primary", use_container_width=True):
        from src.assistant_local import VisionBootLocal
        vb = VisionBootLocal()
        insight = vb.get_smart_analysis(df)
        
        with st.status("Génération du rapport PDF en cours..."):
            pdf_bytes = generate_full_pdf_report(df, insight)
            
        st.download_button(
            label="📥 Télécharger le Rapport Vision-ShopFlow (PDF)",
            data=pdf_bytes,
            file_name=f"rapport_vision_shopflow_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )


def exportable_plot(fig, filename="graphique"):
    """Affiche un graphique avec ses options de téléchargement PNG/PDF."""
    import io

    st.pyplot(fig)

    c1, c2 = st.columns(2)
    with c1:
        buf_png = io.BytesIO()
        fig.savefig(buf_png, format="png", bbox_inches="tight", dpi=300)
        st.download_button(
            label="💾 Image (PNG)",
            data=buf_png.getvalue(),
            file_name=f"{filename}.png",
            mime="image/png",
            key=f"btn_png_{filename}_{hash(filename)}",
        )

    with c2:
        buf_pdf = io.BytesIO()
        fig.savefig(buf_pdf, format="pdf", bbox_inches="tight")
        st.download_button(
            label="📄 Rapport (PDF)",
            data=buf_pdf.getvalue(),
            file_name=f"{filename}.pdf",
            mime="application/pdf",
            key=f"btn_pdf_{filename}_{hash(filename)}",
        )
