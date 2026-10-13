# backend/activate_seller.py
from app import app
from models import db, User
from datetime import datetime, timedelta

def activate_user_as_seller():
    with app.app_context():
        telephone = "0710069791"  # Votre numéro
        user = User.query.filter_by(telephone=telephone).first()
        
        if not user:
            print(f"❌ Utilisateur {telephone} non trouvé")
            return
        
        print(f"👤 Utilisateur: {user.full_name} ({user.telephone})")
        print(f"   Rôle actuel: {user.role}")
        print(f"   Statut: {user.account_status}")  # ✅ Remplacé is_active par account_status
        
        # ✅ Utiliser account_status au lieu de is_active
        user.role = "seller"
        user.account_status = "active"  # ✅ Au lieu de is_active = True
        user.subscription_expires = datetime.utcnow() + timedelta(days=30)
        
        db.session.commit()
        
        print(f"✅ {user.full_name} est maintenant vendeur actif !")
        print(f"   Rôle: {user.role}")
        print(f"   Statut: {user.account_status}")
        print(f"   Abonnement expire le: {user.subscription_expires}")

if __name__ == "__main__":
    activate_user_as_seller()