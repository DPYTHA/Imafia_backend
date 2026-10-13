# backend/config.py
import os
from dotenv import load_dotenv
import sys

# Charger le fichier .env - SPÉCIFIER LE CHEMIN ABSOLU
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

print(f"🔍 Chargement du fichier .env depuis: {env_path}")

class Config:
    # ============================================================
    # BASE DE DONNÉES
    # ============================================================
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    if not database_url:
        database_url = "postgresql://imafia_users:Pytha1991@localhost:5432/imafia"
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # ============================================================
    # JWT
    # ============================================================
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-this-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24 * 30  # 30 jours
    
    # ============================================================
    # GENIUS PAY - Comme Admi.to
    # ============================================================
    GENIUS_PAY_API_URL = os.environ.get("GENIUS_PAY_API_URL", "https://geniuspay.ci/api/v1/merchant")
    GENIUS_PAY_API_KEY = os.environ.get("GENIUS_PAY_API_KEY", "")
    GENIUS_PAY_API_SECRET = os.environ.get("GENIUS_PAY_API_SECRET", "")
    GENIUS_PAY_WEBHOOK_SECRET = os.environ.get("GENIUS_PAY_WEBHOOK_SECRET", "")
    
    GENIUS_PAY_REDIRECT_URL = os.environ.get(
        "GENIUS_PAY_REDIRECT_URL",
        "http://localhost:5000/api/payment/redirect"  
    )
    GENIUS_PAY_CALLBACK_URL = os.environ.get(
        "GENIUS_PAY_CALLBACK_URL",
        "http://localhost:5000/api/payment/webhook"   # 
    )
    
    
    # ============================================================
    # CLOUDINARY - VÉRIFIER LE CHARGEMENT
    # ============================================================
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
    
    # Afficher les valeurs pour vérification
    print(f"📸 Configuration Cloudinary:")
    print(f"   Cloud Name: {CLOUDINARY_CLOUD_NAME if CLOUDINARY_CLOUD_NAME else '⚠️ NON DÉFINI'}")
    print(f"   API Key: {CLOUDINARY_API_KEY[:10] + '...' if CLOUDINARY_API_KEY else '⚠️ NON DÉFINI'}")
    print(f"   API Secret: {'✅ DÉFINI' if CLOUDINARY_API_SECRET else '⚠️ NON DÉFINI'}")
    
    # ============================================================
    # PRIX (comme Admi.to)
    # ============================================================
    SELLER_PRICE = 500  # FCFA/mois 
    BUYER_PRICE = 200   # FCFA/mois 
    
    # Plans disponibles
    PLANS = {
        "buyer": {
            "name": "Acheteur",
            "price": 200,
            "duration": 30,
            "features": [
                "Voir toutes les annonces",
                "Contacter les vendeurs",
                "Sauvegarder des favoris"
            ]
        },
        "seller": {
            "name": "Vendeur",
            "price": 500,
            "duration": 30,
            "features": [
                "Tout ce que Acheteur",
                "Publier des annonces",
                "Mettre en avant ses biens",
                "Statistiques de visite"
            ]
        }
    }