# TechBot Marketplace - Dockerfile optimisé pour performance
# Version: 2.0

FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Création de l'utilisateur non-root
RUN useradd --create-home --shell /bin/bash bot

# Définition du répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Création des répertoires nécessaires
RUN mkdir -p logs uploads wallets && \
    chown -R bot:bot /app

# Changement vers l'utilisateur non-root
USER bot

# Exposition du port (optionnel pour monitoring)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Commande de démarrage optimisée
CMD ["python", "bot_mlt.py"]