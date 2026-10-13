# backend/activate_user.py
from app import app
from models import db, User
from datetime import datetime, timedelta

def activate_user():
    with app.app_context():
        telephone = "0757123619"  # Votre numéro
        user = User.query.filter_by(telephone=telephone).first()
        
        if not user:
            print(f"❌ Utilisateur {telephone} non trouvé")
            return
        
        print(f"👤 {user.full_name} ({user.telephone})")
        print(f"   Statut actuel: {user.account_status}")
        print(f"   Rôle: {user.role}")
        
        user.account_status = "active"
        user.subscription_expires = datetime.utcnow() + timedelta(days=30)
        db.session.commit()
        
        print(f"✅ {user.full_name} activé !")
        print(f"   Statut: {user.account_status}")
        print(f"   Expire le: {user.subscription_expires}")

if __name__ == "__main__":
    activate_user()