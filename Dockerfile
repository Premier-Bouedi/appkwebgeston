# Utilisation d'une image Python ultra-légère
FROM python:3.11-slim

# Évite les écritures de cache .pyc inutiles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système nécessaires (ex: pour matplotlib)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation des bibliothèques
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de l'intégralité du code source
COPY . .

# Exposition du port par défaut de Streamlit
EXPOSE 8501

# Santé de l'application
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Démarrage de Vision-Boot
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
