📦 Vision-ShopFlow : IA & Visualisation E-commerce
Projet Académique - 2ème Année IT Développement Module : Introduction à l'IA et Machine Learning

📝 Présentation du Projet
Vision-ShopFlow est une application intelligente de prédiction de ventes conçue pour les e-commerçants. L'objectif est d'utiliser le Machine Learning pour anticiper la demande des produits en fonction de variables clés comme le prix, la catégorie et les périodes promotionnelles.

Problématique
Les ruptures de stock et le sur-stockage coûtent cher aux entreprises. Ce projet répond à la question : Comment prédire avec précision le volume de ventes futur pour optimiser l'inventaire ?

🚀 Fonctionnalités
Analyse Exploratoire (EDA) : Visualisation des tendances de ventes via des graphiques interactifs.

Prédiction IA : Interface permettant de saisir les caractéristiques d'un produit pour obtenir une estimation des ventes.

Tableau de Bord : Interface web fluide réalisée avec Streamlit.

🛠️ Technologies Utilisées
Langage : Python 3.x

Data Science : Pandas, NumPy, Matplotlib

Machine Learning : Scikit-learn (RandomForestRegressor / LinearRegression)

Déploiement : Streamlit

📂 Structure du Dépôt
Plaintext
├── dataset/
│   └── sales_data.csv       # Jeu de données utilisé
├── notebooks/
│   └── analyse_ia.ipynb     # Notebook de test et d'entraînement
├── app.py                   # Code source de l'application Streamlit
├── model.pkl                # Modèle entraîné (sauvegardé avec Joblib)
├── requirements.txt         # Liste des bibliothèques nécessaires
└── README.md                # Documentation du projet
⚙️ Installation et Utilisation
Cloner le projet

Bash
git clone https://github.com/Cleinn-Magnaga/vision-shopflow.git
cd vision-shopflow
Installer les dépendances

Bash
pip install -r requirements.txt
Lancer l'application

Bash
streamlit run app.py
📊 Méthodologie IA
Nettoyage : Traitement des valeurs manquantes et suppression des doublons.

Features Engineering : Encodage des catégories et normalisation des prix.

Modélisation : Utilisation de l'algorithme Random Forest pour sa robustesse face aux données e-commerce.

Évaluation : Performance mesurée via le R² et la MAE (Mean Absolute Error).

👤 Auteur
Claïnn Magnaga Makelighi (alias Treedji)

Étudiant en 2ème année - OMNIA School of Business and Technology

Filière : Développement Informatique

💡 Conseils pour ton GitHub :
Ajoute un fichier .gitignore : Pour éviter d'envoyer des dossiers inutiles comme __pycache__ ou ton environnement virtuel .venv.

Prends des captures d'écran : Une fois ton application Streamlit lancée, prends une capture d'écran et ajoute-la dans le dossier img/ de ton dépôt, puis affiche-la dans le README avec ![Demo](img/screenshot.png).

Fais des "Commits" clairs : Par exemple : git commit -m "Ajout du modèle de régression" au lieu de git commit -m "update"
