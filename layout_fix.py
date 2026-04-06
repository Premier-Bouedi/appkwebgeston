import sys

def modify_app():
    with open('c:\\Users\\HP\\Desktop\\mak\\app.py', 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    # We want to extract lines 0 to 353 untouched
    # The header starts at line 355 in 1-indexed (index 354)
    out_lines = lines[:354]

    out_lines.append("")
    out_lines.append('main_col, bot_col = st.columns([3, 1])')
    out_lines.append('with main_col:')
    
    # Header replacement
    out_lines.append('    col_logo, col_title = st.columns([1, 6])')
    out_lines.append('    with col_logo:')
    out_lines.append('        if os.path.exists(icon_path):')
    out_lines.append('            st.image(icon_path, width=90)')
    out_lines.append('    with col_title:')
    out_lines.append('        st.title(f"🛒 {APP_NAME}")')
    out_lines.append('        st.caption(APP_TAGLINE)')
    
    # We skip lines 354 to 402 from the original array
    # because they contain the old `col_logo, col_title, col_chat` and the Chatbot code
    
    # Check if lines[354] is indeed the old col_logo
    if "col_logo, col_title, col_chat = st.columns" in lines[354]:
        idx = 403 # start from this index (line 404)
    else:
        # fallback if somehow it drifted
        idx = 354
        while not "if st.session_state.pop(\"import_ok\":" in lines[idx]:
            idx += 1

    # Now we loop through the rest of the file and prefix with 4 spaces!
    for i in range(idx, len(lines)):
        line = lines[i]
        if line.strip() == "":
            out_lines.append("")
        else:
            out_lines.append("    " + line)

    # Finally, append the Chatbot column logic
    chatbot_logic = """
with bot_col:
    st.subheader("💬 Assistant Shoppy")
    st.markdown("---")
    
    # st.container with height creates a scrollable specific pane
    chat_container = st.container(height=500, border=True)
    with chat_container:
        if len(st.session_state.get("shoppy_messages", [])) == 0:
            st.info("Bonjour ! Je suis Shoppy. Tapez **aide** ou **prédiction**.")
        for msg in st.session_state.get("shoppy_messages", []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    
    def on_chat_submit_right():
        if st.session_state.get("shoppy_input_right"):
            prompt = st.session_state.shoppy_input_right
            st.session_state.shoppy_input_right = ""
            st.session_state["shoppy_messages"].append({"role": "user", "content": prompt})
            prompt_lower = prompt.lower()
            reponse_shoppy = ""
            
            if "aide" in prompt_lower or "mode d'emploi" in prompt_lower:
                reponse_shoppy = "Voici comment m'utiliser :\\n1. 📥 **Injecter données CSV**.\\n2. 📈 **L'onglet Analyse**.\\n3. 🤖 **Faire une Prédiction IA**."
            elif "prédict" in prompt_lower or "estimer" in prompt_lower:
                if st.session_state.get("df_cleaned") is None:
                    reponse_shoppy = "⚠️ Veuillez d'abord injecter un fichier valide."
                else:
                    try:
                        import __main__
                        model = getattr(__main__, 'load_persisted_model', lambda: None)()
                        if model is None:
                             reponse_shoppy = f"⚠️ Modèle indisponible."
                        else:
                            try:
                                MODEL_FEATURES = ["Âge_Client", "Quantite"]
                                import pandas as pd
                                input_data = pd.DataFrame({MODEL_FEATURES[0]: [35], MODEL_FEATURES[1]: [2]})
                                raw_pred = float(model.predict(input_data)[0])
                                prediction = max(0.0, raw_pred)
                                reponse_shoppy = f"✅ **Prédiction réussie :** Scikit-learn estime : **{prediction:,.2f} €**."
                            except Exception as e:
                                reponse_shoppy = f"❌ Erreur : {e}"
                    except Exception as e:
                         reponse_shoppy = f"⚠️ Impossible de charger le modèle. {e}"
            else:
                reponse_shoppy = "Tapez **aide** ou **prédiction**."
                
            st.session_state["shoppy_messages"].append({"role": "assistant", "content": reponse_shoppy})
            
    st.text_input("Poser une question à Shoppy...", key="shoppy_input_right", on_change=on_chat_submit_right)
"""
    out_lines.extend(chatbot_logic.strip('\n').split('\n'))

    with open('c:\\Users\\HP\\Desktop\\mak\\app.py', 'w', encoding='utf-8') as f:
        f.write("\n".join(out_lines) + "\n")
    print("Mise a jour du layout terminee avec succes!")

if __name__ == "__main__":
    modify_app()
