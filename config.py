import os
from pathlib import Path

# ==========================================
# CONSTANTES DE L'APPLICATION
# ==========================================
APP_NAME = "VISION-BOOT"
APP_TAGLINE = "Intelligence Artificielle & Gestion E-commerce"

APP_PAGE_DASHBOARD = "Tableau de bord"
APP_PAGE_VISION_SHOP_STOCK = "📦 Gestion du Stock"
APP_PAGE_VISION_SHOP_DASH = "📊 Dashboard IA"
APP_PAGE_QUALITY = "Données"
APP_PAGE_ANALYTICS = "Analyse"
APP_PAGE_FORECAST = "Prédiction (Machine Learning)"
APP_PAGE_SQL_UNIVERSAL = "🔗 Connexion SQL (client)"

# Base SQLite persistante (Vision-Shop)
DATABASE_VISION_SHOP = "vision_shop.db"

# ==========================================
# CHEMINS ET FICHIERS
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_FILENAME = "modele_ia.pkl"
MODEL_PATH = SCRIPT_DIR / MODEL_FILENAME

HISTORIQUE_ROOT = SCRIPT_DIR / "historique_traitements"
HISTORIQUE_CSV_NAME = "df_ecommerce_nettoye.csv"
HISTORIQUE_MAX_ENTREES = 100
SAMPLE_CSV_NAME = "donnees_ventes.csv"
SAMPLE_CSV_PATH = SCRIPT_DIR / SAMPLE_CSV_NAME
VISION_SHOP_DB_PATH = SCRIPT_DIR / DATABASE_VISION_SHOP

icon_path = "logo.png" if os.path.exists("logo.png") else ("logo.png.png" if os.path.exists("logo.png.png") else "logo.png")
app_icon = icon_path if os.path.exists(icon_path) else "🛒"

# ==========================================
# DONNÉES ET DATA SCIENCE
# ==========================================
INJ_LABEL_FILE = "Fichier CSV (téléversement)"
INJ_LABEL_PASTE = "Coller du CSV (texte)"
INJ_LABEL_SAMPLE = f"Fichier local : {SAMPLE_CSV_NAME}"
INJ_LABEL_DB = "Base de données (SQL)"
INJ_LABEL_API = "API (URL — JSON ou CSV)"

REQUIRED_COLS = frozenset(
    {
        "ID_Transaction",
        "Date",
        "Categorie_Produit",
        "Prix_Unitaire",
        "Quantite",
        "Âge_Client",
        "Méthode_Paiement",
        "Satisfaction_Client (1-5)",
    }
)

NUMERIC_PREP_COLS = ("Prix_Unitaire", "Quantite", "Âge_Client")
MODEL_FEATURES = ["Âge_Client", "Quantite"]

RESULTATS_ML_COLONNES = (
    "Horodatage",
    "Age_Client",
    "Quantite",
    "Montant_estime_EUR",
)
