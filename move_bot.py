import sys

def modify_app():
    with open('c:\\Users\\HP\\Desktop\\mak\\app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # The sidebar chatbot block to remove
    bot_sidebar_code = """st.sidebar.subheader("💬 Assistant Shoppy")

if st.sidebar.button("Fermer Shoppy" if st.session_state["shoppy_active"] else "Ouvrir Shoppy", use_container_width=True):
    st.session_state["shoppy_active"] = not st.session_state["shoppy_active"]
    st.rerun()

if st.session_state["shoppy_active"]:
    st.sidebar.markdown("---")
    
    # Conteneur pour l'historique des messages
    chat_container = st.sidebar.container()
    with chat_container:
        if len(st.session_state["shoppy_messages"]) == 0:
            st.info("Bonjour ! Je suis Shoppy. Tapez **aide** ou **prédiction**.")
        for msg in st.session_state["shoppy_messages"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    # Champ de saisie
    def on_chat_submit():
        if st.session_state.shoppy_input:
            prompt = st.session_state.shoppy_input
            st.session_state.shoppy_input = "" # Clear input
            st.session_state["shoppy_messages"].append({"role": "user", "content": prompt})
            
            prompt_lower = prompt.lower()
            reponse_shoppy = ""
            
            if "aide" in prompt_lower or "mode d'emploi" in prompt_lower:
                reponse_shoppy = "Voici comment m'utiliser :\\n1. 📥 **Injecter mes données CSV** via le panneau d'injection.\\n2. 📈 **Voir l'Analyse Intelligente** (Pandas Dynamic) dans l'onglet Analyse.\\n3. 🤖 **Faire une Prédiction IA** (Scikit-learn Persistence) sur la page Prédiction, ou directement ici."
            elif "prédict" in prompt_lower or "estimer" in prompt_lower:
                if st.session_state.get("df_cleaned") is None:
                    reponse_shoppy = "⚠️ Sécurité : Veuillez d'abord injecter un fichier de données e-commerce valide via la barre latérale."
                else:
                    model = load_persisted_model()
                    if model is None:
                         reponse_shoppy = f"⚠️ Modèle indisponible. Le fichier `{MODEL_FILENAME}` est requis."
                    else:
                        try:
                            input_data = pd.DataFrame({
                                MODEL_FEATURES[0]: [35],
                                MODEL_FEATURES[1]: [2]
                            })
                            raw_pred = float(model.predict(input_data)[0])
                            prediction = max(0.0, raw_pred)
                            reponse_shoppy = f"✅ **Prédiction IA réussie :** Pour un âge par défaut (35 ans) et 2 articles, l'estimation Scikit-learn est de **{prediction:,.2f} €**."
                        except Exception as e:
                            reponse_shoppy = f"❌ Erreur lors de la prédiction : {e}"
            else:
                reponse_shoppy = "Hmm, je n'ai pas compris. Tapez **aide** ou **prédiction** pour interagir avec l'IA."
                
            st.session_state["shoppy_messages"].append({"role": "assistant", "content": reponse_shoppy})

    # On utilise st.text_input au lieu de chat_input si c'est dans la sidebar pour éviter les restrictions de design de Streamlit.
    st.sidebar.text_input("Posez une question à Shoppy", key="shoppy_input", on_change=on_chat_submit)

"""
    if bot_sidebar_code in content:
        content = content.replace(bot_sidebar_code, "")
    else:
        print("Bot sidebar code not found perfectly. Will try heuristics.")
        # We can try to just cut it dynamically if needed.

    # Now let's find the page if-elif block and indent it.
    lines = content.split('\n')
    new_lines = []
    
    inside_page_block = False
    
    bot_main_code = """
# -- Configuration du Chatbot sur la droite --
if st.session_state.get("shoppy_active", False):
    col_main, col_chat = st.columns([3, 1])
else:
    col_main = st.container()
    col_chat = None

# Bouton de contrôle du Chatbot visible en haut à droite
c1, c2 = st.columns([5, 1])
with c2:
    if st.button("Fermer Shoppy" if st.session_state.get("shoppy_active") else "💬 Ouvrir Shoppy"):
        st.session_state["shoppy_active"] = not st.session_state.get("shoppy_active", False)
        st.rerun()

with col_main:
"""
    
    # We will also insert the Chatbot logic into col_chat
    bot_chat_logic = """
if col_chat is not None:
    with col_chat:
        st.subheader("💬 Assistant Shoppy")
        st.markdown("---")
        
        chat_container = st.container()
        with chat_container:
            if len(st.session_state.get("shoppy_messages", [])) == 0:
                st.info("Bonjour ! Je suis Shoppy. Tapez **aide** ou **prédiction**.")
            for msg in st.session_state.get("shoppy_messages", []):
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        def on_chat_submit_main():
            if st.session_state.shoppy_input_main:
                prompt = st.session_state.shoppy_input_main
                st.session_state.shoppy_input_main = ""
                st.session_state["shoppy_messages"].append({"role": "user", "content": prompt})
                prompt_lower = prompt.lower()
                reponse_shoppy = ""
                
                if "aide" in prompt_lower or "mode d'emploi" in prompt_lower:
                    reponse_shoppy = "Voici comment m'utiliser :\\n1. 📥 **Injecter mes données CSV** via le panneau d'injection.\\n2. 📈 **Voir l'Analyse Intelligente** dans l'onglet Analyse.\\n3. 🤖 **Faire une Prédiction IA**."
                elif "prédict" in prompt_lower or "estimer" in prompt_lower:
                    if st.session_state.get("df_cleaned") is None:
                        reponse_shoppy = "⚠️ Sécurité : Veuillez d'abord injecter un fichier valide."
                    else:
                        model = load_persisted_model()
                        if model is None:
                             reponse_shoppy = f"⚠️ Modèle indisponible."
                        else:
                            try:
                                input_data = pd.DataFrame({MODEL_FEATURES[0]: [35], MODEL_FEATURES[1]: [2]})
                                pred = float(model.predict(input_data)[0])
                                reponse_shoppy = f"✅ **Prédiction réussie :** Estimation Scikit-learn : **{max(0.0, pred):,.2f} €**."
                            except Exception as e:
                                reponse_shoppy = f"❌ Erreur : {e}"
                else:
                    reponse_shoppy = "Hmm, je n'ai pas compris. Tapez **aide** ou **prédiction**."
                    
                st.session_state["shoppy_messages"].append({"role": "assistant", "content": reponse_shoppy})
                
        st.text_input("Posez une question", key="shoppy_input_main", on_change=on_chat_submit_main)
"""

    for i, line in enumerate(lines):
        if line.startswith("if page == APP_PAGE_DASHBOARD:"):
            new_lines.extend(bot_main_code.strip('\n').split('\n'))
            inside_page_block = True
            new_lines.append("    " + line)
        elif inside_page_block:
            if line.startswith("st.divider()") and "st.caption(f\"©" in "\n".join(lines[i:i+3]):
                # End of page block
                inside_page_block = False
                new_lines.extend(bot_chat_logic.strip('\n').split('\n'))
                new_lines.append(line)
            else:
                if line.strip() == "":
                    new_lines.append("")
                else:
                    new_lines.append("    " + line)
        else:
            new_lines.append(line)

    with open('c:\\Users\\HP\\Desktop\\mak\\app.py', 'w', encoding='utf-8') as f:
        f.write("\n".join(new_lines))
    print("Modification terminee.")

if __name__ == "__main__":
    modify_app()
