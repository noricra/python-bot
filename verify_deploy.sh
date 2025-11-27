#!/bin/bash

# Script de vérification pré-déploiement Railway
# Vérifie que tous les fichiers nécessaires sont présents

echo "🔍 VÉRIFICATION PRÉ-DÉPLOIEMENT RAILWAY"
echo "========================================"
echo ""

ERRORS=0

# Vérifier les fichiers requis
echo "📋 Vérification des fichiers..."

required_files=(
    ".gitignore"
    "Procfile"
    "runtime.txt"
    "requirements.txt"
    "railway.json"
    ".env.example"
    "app/main.py"
    "app/core/db_pool.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file MANQUANT"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""

# Vérifier que .env n'est PAS commité
echo "🔒 Vérification sécurité..."
if [ -f ".env" ]; then
    if git ls-files --error-unmatch .env 2>/dev/null; then
        echo "  ❌ .env est dans Git ! DANGER ! Retirer immédiatement !"
        echo "     Exécuter : git rm --cached .env"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ .env existe mais n'est pas dans Git"
    fi
else
    echo "  ⚠️  .env n'existe pas (créer à partir de .env.example)"
fi

echo ""

# Vérifier Git
echo "🔧 Vérification Git..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "  ✅ Repository Git initialisé"
    
    # Vérifier s'il y a des modifications non commitées
    if [[ -n $(git status -s) ]]; then
        echo "  ⚠️  Modifications non commitées détectées :"
        git status -s
        echo "     Exécuter : git add . && git commit -m 'Message'"
    else
        echo "  ✅ Pas de modifications non commitées"
    fi
    
    # Vérifier s'il y a un remote configuré
    if git remote -v | grep -q "origin"; then
        echo "  ✅ Remote 'origin' configuré"
        git remote -v | head -2
    else
        echo "  ⚠️  Aucun remote configuré"
        echo "     Exécuter : git remote add origin https://github.com/USERNAME/REPO.git"
    fi
else
    echo "  ❌ Git non initialisé"
    echo "     Exécuter : git init"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Vérifier les variables d'environnement nécessaires
echo "🔑 Variables d'environnement requises..."
required_vars=(
    "BOT_TOKEN"
    "ADMIN_USER_ID"
    "NOWPAYMENTS_API_KEY"
    "B2_KEY_ID"
    "B2_APPLICATION_KEY"
    "SMTP_USER"
    "SMTP_PASSWORD"
)

if [ -f ".env" ]; then
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env; then
            value=$(grep "^${var}=" .env | cut -d '=' -f2)
            if [ -z "$value" ] || [ "$value" == "your_*" ] || [ "$value" == "[*" ]; then
                echo "  ⚠️  $var défini mais valeur par défaut"
            else
                echo "  ✅ $var"
            fi
        else
            echo "  ❌ $var manquant"
        fi
    done
else
    echo "  ⚠️  Fichier .env non trouvé (vérification impossible)"
fi

echo ""
echo "========================================"

if [ $ERRORS -eq 0 ]; then
    echo "✅ TOUT EST PRÊT POUR LE DÉPLOIEMENT !"
    echo ""
    echo "Prochaines étapes :"
    echo "1. git add ."
    echo "2. git commit -m 'Ready for Railway deployment'"
    echo "3. git push origin main"
    echo "4. Déployer sur Railway (voir DEPLOYMENT.md)"
    exit 0
else
    echo "❌ $ERRORS ERREUR(S) DÉTECTÉE(S)"
    echo ""
    echo "Corrigez les erreurs avant de déployer."
    exit 1
fi
