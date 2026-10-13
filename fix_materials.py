# backend/fix_materials.py
from app import app
from models import db, Material, User

def fix_materials():
    with app.app_context():
        # Récupérer tous les matériaux
        materials = Material.query.all()
        
        for material in materials:
            print(f"🧱 Matériau: {material.id} - {material.title}")
            print(f"   Seller ID actuel: {material.seller_id}")
            
            # Si seller_id est None ou 0, le définir sur un utilisateur existant
            if not material.seller_id or material.seller_id == 0:
                # Prendre le premier utilisateur vendeur
                seller = User.query.filter_by(role="seller").first()
                if seller:
                    material.seller_id = seller.id
                    print(f"   ✅ Seller ID mis à jour: {material.seller_id}")
                else:
                    print(f"   ❌ Aucun vendeur trouvé")
        
        db.session.commit()
        print("✅ Matériaux corrigés")

if __name__ == "__main__":
    fix_materials()