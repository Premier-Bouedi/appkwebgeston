import pickle
import pandas as pd
from typing import Optional, Any
from pathlib import Path
from datetime import datetime

MODEL_VERSION = "2.0.0"  # Version actuelle (Audit Suite)

class ModelManager:
    """Système Auto-ML Premium : Sélectionne le meilleur algo et gère le versioning metadata."""
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.model = None
        self.feature_names = []
        self.version = "N/A"
        self.updated_at = "Jamais"
        self._load_model_safe()
        self.metrics = {"r2": 0.0, "mse": 0.0, "best_algo": "N/A"}

    def _load_model_safe(self) -> None:
        """Charge le modèle et vérifie la compatibilité de version."""
        if not self.model_path.is_file():
            return
        try:
            with open(self.model_path, "rb") as f:
                container = pickle.load(f)
            
            # Support du format legacy (sinon dictionnaire)
            if isinstance(container, dict) and container.get("version") == MODEL_VERSION:
                self.model = container.get("model")
                self.feature_names = container.get("features", [])
                self.version = container.get("version")
                self.updated_at = container.get("updated_at", "Date inconnue")
            else:
                # Incompatibilité détectée
                self.version = "INCOMPATIBLE"
        except Exception:
            self.model = None

    def auto_train(self, df: pd.DataFrame):
        """Compétition entre modèles : Entraîne et choisit le plus précis (avec variables catégorielles)."""
        from sklearn.model_selection import train_test_split
        from sklearn.linear_model import LinearRegression
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import r2_score, mean_squared_error
        
        # 1. Barrière de sécurité : Dataset trop petit
        if len(df) < 8:
            self.metrics["best_algo"] = "N/A (Données insuffisantes)"
            return

        # 2. Feature Engineering : Prise en compte des catégories
        features = ["Âge_Client", "Quantite"]
        if "Categorie_Produit" in df.columns:
            # Encodage One-Hot (Dummies)
            X = pd.get_dummies(df[["Âge_Client", "Quantite", "Categorie_Produit"]], columns=["Categorie_Produit"])
        else:
            X = df[["Âge_Client", "Quantite"]]
            
        y = df["Montant_Total"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # 1. Modèle Linéaire
        lin_reg = LinearRegression()
        lin_reg.fit(X_train, y_train)
        y_pred_lin = lin_reg.predict(X_test)
        score_lin = r2_score(y_test, y_pred_lin)

        # 2. Random Forest
        rf_reg = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_reg.fit(X_train, y_train)
        y_pred_rf = rf_reg.predict(X_test)
        score_rf = r2_score(y_test, y_pred_rf)

        # Sélection du gagnant
        if score_rf > score_lin:
            self.model = rf_reg
            # On garde trace des colonnes pour les prédictions futures
            self.feature_names = X.columns.tolist()
            self.metrics["best_algo"] = "Random Forest (Complexe)"
            self.metrics["r2"] = score_rf
            self.metrics["mse"] = mean_squared_error(y_test, y_pred_rf)
        else:
            self.model = lin_reg
            self.feature_names = X.columns.tolist()
            self.metrics["best_algo"] = "Régression Linéaire (Stable)"
            self.metrics["r2"] = score_lin
            self.metrics["mse"] = mean_squared_error(y_test, y_pred_lin)

        # Profilage
        avg_price = df["Prix_Unitaire"].mean()
        avg_basket = df["Montant_Total"].mean()
        
        if avg_price > 50 or avg_basket > 100:
            self.metrics["store_profile"] = "💎 Luxe / Panier Élevé"
            self.metrics["strategy"] = "Fidélisation et Service Client Premium"
        else:
            self.metrics["store_profile"] = "📦 Volume / Panier Bas"
            self.metrics["strategy"] = "Optimisation logistique et Promotions de masse"

        # Persistance disque avec Métadonnées (Format Premium)
        data_to_save = {
            "version": MODEL_VERSION,
            "model": self.model,
            "features": self.feature_names,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.model_path, "wb") as f:
            pickle.dump(data_to_save, f)
        
        self.version = MODEL_VERSION
        self.updated_at = data_to_save["updated_at"]

    def predict_amount(self, age: int, quantite: int, categorie: str = "Divers") -> float:
        """Prédit le montant estimé en utilisant le meilleur modèle (supporte les catégories)."""
        if not self.model:
            raise ValueError("Vision-Boot : Aucun modèle n'est encore entraîné.")
        
        # 1. Création de l'input de base
        input_dict = {"Âge_Client": [age], "Quantite": [quantite]}
        
        # 2. Re-création des colonnes Dummies si nécessaire
        if hasattr(self, "feature_names"):
            # On initialise toutes les colonnes à 0
            for col in self.feature_names:
                if col not in input_dict:
                    input_dict[col] = [0]
            
            # On active la bonne catégorie
            target_col = f"Categorie_Produit_{categorie}"
            if target_col in input_dict:
                input_dict[target_col] = [1]
            
            # Reconstruction du DataFrame dans l'ordre exact imposé à l'entraînement
            input_df = pd.DataFrame(input_dict)[self.feature_names]
        else:
            input_df = pd.DataFrame(input_dict)
            
        raw_pred = float(self.model.predict(input_df)[0])
        return max(0.0, raw_pred)
