import requests
import streamlit as st

class FirebaseAuth:
    """
    Service d'authentification Firebase (Traduction Python du AuthService Dart).
    Utilise l'API REST de Firebase Auth.
    """
    
    def __init__(self):
        self.api_key = st.secrets.get("firebase", {}).get("api_key", "...")
        # Liste des valeurs qui indiquent une clé non encore configurée
        placeholders = ["...", "", None, "VOTRE_CLE_API_ICI", "TA_CLE_ICI"]
        self.is_configured = self.api_key not in placeholders
        self.base_url = "https://identitytoolkit.googleapis.com/v1/accounts"

    def login(self, email, password):
        """
        Connecte un utilisateur ou simule un login si en mode démo.
        """
        if not self.is_configured:
            # Mode Démo / Bypass
            return {
                "displayName": "Utilisateur Démo",
                "email": email or "demo@vision-boot.com",
                "localId": "GUEST_USER_ID"
            }, None
        url = f"{self.base_url}:signInWithPassword?key={self.api_key}"
        payload = {
            "email": email.strip(),
            "password": password,
            "returnSecureToken": True
        }
        
        try:
            response = requests.post(url, json=payload)
            data = response.json()
            
            if response.status_code == 200:
                return data, None
            else:
                error_code = data.get("error", {}).get("message", "UNKNOWN_ERROR")
                return None, self._translate_error(error_code)
        except Exception as e:
            return None, f"Erreur de connexion : {str(e)}"

    def register(self, email, password, display_name):
        """
        Crée un nouvel utilisateur (ou simulé si en mode démo).
        """
        if not self.is_configured:
            return {
                "displayName": display_name or "Nouvel Utilisateur Démo",
                "email": email,
                "localId": "GUEST_USER_ID"
            }, None
        url_signup = f"{self.base_url}:signUp?key={self.api_key}"
        payload_signup = {
            "email": email.strip(),
            "password": password,
            "returnSecureToken": True
        }
        
        try:
            # 1. Création du compte
            res_signup = requests.post(url_signup, json=payload_signup)
            data_signup = res_signup.json()
            
            if res_signup.status_code != 200:
                error_code = data_signup.get("error", {}).get("message", "UNKNOWN_ERROR")
                return None, self._translate_error(error_code)
            
            # 2. Mise à jour du Display Name
            id_token = data_signup.get("idToken")
            url_update = f"{self.base_url}:update?key={self.api_key}"
            payload_update = {
                "idToken": id_token,
                "displayName": display_name.strip(),
                "returnSecureToken": True
            }
            res_update = requests.post(url_update, json=payload_update)
            
            if res_update.status_code == 200:
                return res_update.json(), None
            else:
                return data_signup, "Utilisateur créé, mais impossible de mettre à jour le nom."
                
        except Exception as e:
            return None, f"Erreur d'inscription : {str(e)}"

    def _translate_error(self, code):
        """Traduit les codes d'erreur Firebase en messages conviviaux."""
        errors = {
            "EMAIL_NOT_FOUND": "Email non trouvé. Veuillez vérifier votre adresse ou vous inscrire.",
            "INVALID_PASSWORD": "Mot de passe incorrect.",
            "USER_DISABLED": "Ce compte a été désactivé.",
            "EMAIL_EXISTS": "Cette adresse email est déjà utilisée par un autre compte.",
            "OPERATION_NOT_ALLOWED": "L'inscription par mot de passe n'est pas activée dans Firebase.",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Trop de tentatives. Réessayez plus tard.",
            "WEAK_PASSWORD": "Le mot de passe doit contenir au moins 6 caractères.",
            "INVALID_EMAIL": "L'adresse email est mal formatée."
        }
        return errors.get(code, f"Erreur Firebase : {code}")

def init_auth():
    """Initialise l'objet d'authentification dans la session Streamlit."""
    if "firebase_auth" not in st.session_state:
        st.session_state.firebase_auth = FirebaseAuth()
    if "user" not in st.session_state:
        st.session_state.user = None
