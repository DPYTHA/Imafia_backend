# backend/app.py 
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity,
    verify_jwt_in_request, get_jwt
)
from datetime import datetime, timedelta
from functools import wraps
import bcrypt
import cloudinary.uploader

# Fix: Use relative imports 
from config import Config
from models import (
    db, User, Property, Material, Service,
    Rental, Payment, PaymentEvent, Favorite,
    Notification
)
from cloudinary_config import upload_image, upload_avatar, upload_property_image
from payments import (
    create_genius_pay_payment, 
    activate_subscription, 
    verify_genius_pay_payment,
    verify_genius_pay_webhook_signature,
    get_subscription_status,
    log_payment_event
)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins="*", supports_credentials=True)
db.init_app(app)
jwt = JWTManager(app)

# ============================================================
# HELPERS
# ============================================================
def require_active_subscription(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        if user.account_status != "active" or (user.subscription_expires and user.subscription_expires < datetime.utcnow()):
            return jsonify({
                "error": "Abonnement requis",
                "requires_subscription": True,
                "plan_type": "buyer" if user.role == "buyer" else "seller"
            }), 402
        return f(*args, **kwargs)
    return wrapper

def require_seller(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        if user.role != "seller":
            return jsonify({"error": "Seuls les vendeurs peuvent effectuer cette action"}), 403
        return f(*args, **kwargs)
    return wrapper

# ============================================================
# AUTH - UNIQUEMENT PAR TÉLÉPHONE
# ============================================================
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    telephone = data.get("telephone", "").strip()
    full_name = data.get("full_name", "").strip()
    password = data.get("password", "")
    role = data.get("role", "buyer")
    avatar_url = data.get("avatar_url", "")
    
    if not telephone or len(telephone) < 8:
        return jsonify({"error": "Numéro de téléphone invalide"}), 400
    
    if User.query.filter_by(telephone=telephone).first():
        return jsonify({"error": "Ce numéro est déjà utilisé"}), 409
    
    user = User(
        telephone=telephone,
        full_name=full_name,
        role=role,
        account_status="inactive",
        avatar_url=avatar_url
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    token = create_access_token(identity=str(user.id), expires_delta=timedelta(days=30))
    return jsonify({"token": token, "user": user.to_dict()}), 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    telephone = data.get("telephone", "").strip()
    password = data.get("password", "")
    
    user = User.query.filter_by(telephone=telephone).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Téléphone ou mot de passe incorrect"}), 401
    
    token = create_access_token(identity=str(user.id), expires_delta=timedelta(days=30))
    return jsonify({"token": token, "user": user.to_dict()}), 200




# ============================================================
# MOT DE PASSE OUBLIÉ - VERSION ULTRA SIMPLE
# ============================================================

@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password_simple():
    """Génère un nouveau mot de passe aléatoire pour l'utilisateur"""
    try:
        data = request.get_json()
        telephone = data.get("telephone", "").strip()
        
        if not telephone or len(telephone) < 8:
            return jsonify({"error": "Numéro de téléphone invalide"}), 400
        
        user = User.query.filter_by(telephone=telephone).first()
        
        if not user:
            return jsonify({
                "success": False,
                "message": "Ce numéro n'est pas enregistré"
            }), 404
        
        # Génère un mot de passe aléatoire (8 caractères)
        import random
        import string
        characters = string.ascii_letters + string.digits
        new_password = ''.join(random.choice(characters) for _ in range(8))
        
        # Met à jour le mot de passe
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Mot de passe réinitialisé avec succès",
            "new_password": new_password,
            "telephone": user.telephone
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/me", methods=["GET"])
@jwt_required()
def me():
    user = User.query.get(get_jwt_identity())
    return jsonify(user.to_dict()), 200

@app.route("/api/auth/me", methods=["PUT"])
@jwt_required()
def update_profile():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        
        data = request.get_json()
        
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'email' in data:
            user.email = data['email']
        if 'bio' in data:
            user.bio = data['bio']
        if 'location' in data:
            user.location = data['location']
        
        db.session.commit()
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        print(f"❌ Erreur mise à jour profil: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/auth/avatar", methods=["POST"])
@jwt_required()
def update_user_avatar():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        
        if 'avatar' not in request.files:
            return jsonify({"error": "Aucune image"}), 400
        
        file = request.files['avatar']
        if file.filename == '':
            return jsonify({"error": "Fichier vide"}), 400
        
        url = upload_avatar(file, user_id)
        if url:
            user.avatar_url = url
            db.session.commit()
            return jsonify({"avatar_url": url}), 200
        else:
            fallback_url = f"https://ui-avatars.com/api/?name={user.full_name}&size=200&background=0D5CC9&color=fff&bold=true"
            user.avatar_url = fallback_url
            db.session.commit()
            return jsonify({"avatar_url": fallback_url, "fallback": True}), 200
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================
# FAVORIS
# ============================================================

VALID_FAVORITE_TYPES = {"property", "material", "service", "rental"}


def get_current_user_id():
    """Retourne l'identifiant numérique de l'utilisateur connecté."""
    identity = get_jwt_identity()

    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


@app.route("/api/favorites", methods=["GET"])
@jwt_required()
def get_favorites():
    """Récupère les favoris de l'utilisateur connecté."""
    try:
        user_id = get_current_user_id()

        if user_id is None:
            return jsonify({"error": "Identité utilisateur invalide"}), 401

        favorites = (
            Favorite.query
            .filter_by(user_id=user_id)
            .order_by(Favorite.created_at.desc())
            .all()
        )

        # Le frontend reçoit directement une liste.
        return jsonify([favorite.to_dict() for favorite in favorites]), 200

    except Exception:
        db.session.rollback()
        app.logger.exception("Erreur lors de la récupération des favoris")
        return jsonify({"error": "Impossible de récupérer les favoris"}), 500


@app.route("/api/favorites", methods=["POST"])
@jwt_required()
def add_favorite():
    """Ajoute un favori sans créer de doublon."""
    try:
        user_id = get_current_user_id()

        if user_id is None:
            return jsonify({"error": "Identité utilisateur invalide"}), 401

        data = request.get_json(silent=True) or {}

        item_id = data.get("item_id")
        item_type = data.get("item_type")

        try:
            # Refuse les booléens et les identifiants non numériques.
            if isinstance(item_id, bool):
                raise ValueError()
            item_id = int(item_id)
        except (TypeError, ValueError):
            return jsonify({"error": "item_id doit être un entier valide"}), 400

        if item_id <= 0:
            return jsonify({"error": "item_id doit être supérieur à zéro"}), 400

        if not isinstance(item_type, str):
            return jsonify({"error": "item_type est requis"}), 400

        item_type = item_type.strip().lower()

        if item_type not in VALID_FAVORITE_TYPES:
            return jsonify({
                "error": "Type de favori invalide",
                "allowed_types": sorted(VALID_FAVORITE_TYPES)
            }), 400

        existing = Favorite.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            item_type=item_type
        ).first()

        if existing:
            return jsonify({
                "message": "Ce favori existe déjà",
                "favorite": existing.to_dict()
            }), 200

        favorite = Favorite(
            user_id=user_id,
            item_id=item_id,
            item_type=item_type
        )

        db.session.add(favorite)
        db.session.commit()

        return jsonify({
            "message": "Favori ajouté",
            "favorite": favorite.to_dict()
        }), 201

    except Exception:
        db.session.rollback()
        app.logger.exception("Erreur lors de l'ajout d'un favori")
        return jsonify({"error": "Impossible d'ajouter ce favori"}), 500


@app.route("/api/favorites/<int:favorite_id>", methods=["DELETE"])
@jwt_required()
def remove_favorite(favorite_id):
    """Supprime un favori par son ID, uniquement pour son propriétaire."""
    try:
        user_id = get_current_user_id()

        if user_id is None:
            return jsonify({"error": "Identité utilisateur invalide"}), 401

        favorite = Favorite.query.filter_by(
            id=favorite_id,
            user_id=user_id
        ).first()

        if not favorite:
            return jsonify({"error": "Favori non trouvé"}), 404

        db.session.delete(favorite)
        db.session.commit()

        return jsonify({"message": "Favori supprimé"}), 200

    except Exception:
        db.session.rollback()
        app.logger.exception("Erreur lors de la suppression d'un favori")
        return jsonify({"error": "Impossible de supprimer ce favori"}), 500


@app.route("/api/favorites/item/<int:item_id>", methods=["DELETE"])
@jwt_required()
def remove_favorite_by_item(item_id):
    """
    Supprime un favori en utilisant l'ID de l'annonce et son type.
    Exemple : DELETE /api/favorites/item/12?item_type=property
    """
    try:
        user_id = get_current_user_id()

        if user_id is None:
            return jsonify({"error": "Identité utilisateur invalide"}), 401

        item_type = request.args.get("item_type", "").strip().lower()

        if item_type not in VALID_FAVORITE_TYPES:
            return jsonify({
                "error": "item_type est requis ou invalide",
                "allowed_types": sorted(VALID_FAVORITE_TYPES)
            }), 400

        favorite = Favorite.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            item_type=item_type
        ).first()

        if not favorite:
            return jsonify({"error": "Favori non trouvé"}), 404

        db.session.delete(favorite)
        db.session.commit()

        return jsonify({"message": "Favori supprimé"}), 200

    except Exception:
        db.session.rollback()
        app.logger.exception("Erreur lors de la suppression du favori par annonce")
        return jsonify({"error": "Impossible de supprimer ce favori"}), 500


# ============================================================
# MES ANNONCES
# ============================================================
@app.route("/api/my-listings", methods=["GET"])
@jwt_required()
def get_my_listings():
    """Retourne toutes les annonces de l'utilisateur connecté."""
    try:
        user_id = int(get_jwt_identity())

        listings = []

        # ----------------------------------------------------
        # PROPRIÉTÉS
        # ----------------------------------------------------
        properties = (
            Property.query
            .filter(Property.seller_id == user_id)
            .order_by(Property.created_at.desc())
            .all()
        )

        for item in properties:
            data = item.to_dict()

            data["id"] = item.id
            data["type"] = "property"
            data["is_published"] = bool(item.is_published)

            if not isinstance(data.get("image_urls"), list):
                data["image_urls"] = []

            listings.append(data)

        # ----------------------------------------------------
        # MATÉRIAUX
        # ----------------------------------------------------
        materials = (
            Material.query
            .filter(Material.seller_id == user_id)
            .order_by(Material.created_at.desc())
            .all()
        )

        for item in materials:
            data = item.to_dict()

            data["id"] = item.id
            data["type"] = "material"
            data["is_published"] = bool(item.is_published)

            if not isinstance(data.get("image_urls"), list):
                data["image_urls"] = []

            listings.append(data)

        # ----------------------------------------------------
        # SERVICES
        # ----------------------------------------------------
        services = (
            Service.query
            .filter(Service.provider_id == user_id)
            .order_by(Service.created_at.desc())
            .all()
        )

        for item in services:
            data = item.to_dict()

            data["id"] = item.id
            data["type"] = "service"
            data["is_published"] = bool(item.is_published)

            if not isinstance(data.get("image_urls"), list):
                data["image_urls"] = []

            listings.append(data)

        # ----------------------------------------------------
        # LOCATIONS
        # ----------------------------------------------------
        rentals = (
            Rental.query
            .filter(Rental.owner_id == user_id)
            .order_by(Rental.created_at.desc())
            .all()
        )

        for item in rentals:
            data = item.to_dict()

            data["id"] = item.id
            data["type"] = "rental"
            data["is_published"] = bool(item.is_published)

            if not isinstance(data.get("image_urls"), list):
                data["image_urls"] = []

            listings.append(data)

        # ----------------------------------------------------
        # TRI
        # ----------------------------------------------------
        listings.sort(
            key=lambda item: item.get("created_at") or "",
            reverse=True
        )

        return jsonify(listings), 200

    except (TypeError, ValueError):
        return jsonify({
            "error": "Identité utilisateur invalide"
        }), 401

    except Exception as e:
        print(f"❌ Erreur récupération de mes annonces: {e}")

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": "Impossible de récupérer vos annonces"
        }), 500
# ============================================================
# GESTION GÉNÉRIQUE DES ANNONCES
# ============================================================

@app.route("/api/listings/<string:listing_type>/<int:listing_id>", methods=["PUT"])
@jwt_required()
def update_listing(listing_type, listing_id):
    """
    Modification générique d'une annonce.
    
    listing_type:
    - property
    - material
    - service
    - rental
    """
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        print(
            f"✏️ UPDATE LISTING - type={listing_type}, "
            f"id={listing_id}, user={user_id}"
        )

        # ----------------------------------------------------
        # PROPERTY
        # ----------------------------------------------------
        if listing_type == "property":
            item = Property.query.get_or_404(listing_id)

            if int(item.seller_id) != user_id:
                return jsonify({"error": "Non autorisé"}), 403

            if "title" in data:
                item.title = data["title"]

            if "description" in data:
                item.description = data["description"]

            if "price" in data and data["price"] is not None:
                item.price = float(data["price"])

            if "location" in data:
                item.location = data["location"]

            if "property_type" in data:
                item.property_type = data["property_type"]

            if "bedrooms" in data and data["bedrooms"] is not None:
                item.bedrooms = int(data["bedrooms"])

            if "bathrooms" in data and data["bathrooms"] is not None:
                item.bathrooms = int(data["bathrooms"])

            if "surface" in data and data["surface"] is not None:
                item.surface = float(data["surface"])

            if "land_surface" in data and data["land_surface"] is not None:
                item.land_surface = float(data["land_surface"])

            if "is_published" in data:
                item.is_published = bool(data["is_published"])

            db.session.commit()

            result = item.to_dict()
            result["type"] = "property"
            result["is_published"] = bool(item.is_published)

            return jsonify(result), 200

        # ----------------------------------------------------
        # MATERIAL
        # ----------------------------------------------------
        elif listing_type == "material":
            item = Material.query.get_or_404(listing_id)

            if int(item.seller_id) != user_id:
                return jsonify({"error": "Non autorisé"}), 403

            if "title" in data:
                item.title = data["title"]

            if "description" in data:
                item.description = data["description"]

            if "price_per_unit" in data and data["price_per_unit"] is not None:
                item.price_per_unit = float(data["price_per_unit"])

            if "quantity" in data and data["quantity"] is not None:
                item.quantity = float(data["quantity"])

            if "unit" in data:
                item.unit = data["unit"]

            if "category" in data:
                item.category = data["category"]

            if "location" in data:
                item.location = data["location"]

            if "is_published" in data:
                item.is_published = bool(data["is_published"])

            db.session.commit()

            result = item.to_dict()
            result["type"] = "material"
            result["is_published"] = bool(item.is_published)

            return jsonify(result), 200

        # ----------------------------------------------------
        # SERVICE
        # ----------------------------------------------------
        elif listing_type == "service":
            item = Service.query.get_or_404(listing_id)

            if int(item.provider_id) != user_id:
                return jsonify({"error": "Non autorisé"}), 403

            if "title" in data:
                item.title = data["title"]

            if "description" in data:
                item.description = data["description"]

            if "service_type" in data:
                item.service_type = data["service_type"]

            if "price_estimate" in data:
                if data["price_estimate"] in (None, ""):
                    item.price_estimate = None
                else:
                    item.price_estimate = float(data["price_estimate"])

            if "location" in data:
                item.location = data["location"]

            if "is_published" in data:
                item.is_published = bool(data["is_published"])

            db.session.commit()

            result = item.to_dict()
            result["type"] = "service"
            result["is_published"] = bool(item.is_published)

            return jsonify(result), 200

        # ----------------------------------------------------
        # RENTAL
        # ----------------------------------------------------
        elif listing_type == "rental":
            item = Rental.query.get_or_404(listing_id)

            if int(item.owner_id) != user_id:
                return jsonify({"error": "Non autorisé"}), 403

            if "title" in data:
                item.title = data["title"]

            if "description" in data:
                item.description = data["description"]

            if "price_per_night" in data and data["price_per_night"] is not None:
                item.price_per_night = float(data["price_per_night"])

            if "rental_type" in data:
                item.rental_type = data["rental_type"]

            if "bedrooms" in data and data["bedrooms"] is not None:
                item.bedrooms = int(data["bedrooms"])

            if "bathrooms" in data and data["bathrooms"] is not None:
                item.bathrooms = int(data["bathrooms"])

            if "max_guests" in data and data["max_guests"] is not None:
                item.max_guests = int(data["max_guests"])

            if "location" in data:
                item.location = data["location"]

            if "is_published" in data:
                item.is_published = bool(data["is_published"])

            if "available_from" in data:
                item.available_from = parse_date(data["available_from"])

            if "available_to" in data:
                item.available_to = parse_date(data["available_to"])

            db.session.commit()

            result = item.to_dict()
            result["type"] = "rental"
            result["is_published"] = bool(item.is_published)

            return jsonify(result), 200

        else:
            return jsonify({
                "error": "Type d'annonce invalide",
                "allowed_types": [
                    "property",
                    "material",
                    "service",
                    "rental"
                ]
            }), 400

    except Exception as e:
        db.session.rollback()

        print(f"❌ Erreur modification annonce: {e}")

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/api/listings/<string:listing_type>/<int:listing_id>", methods=["DELETE"])
@jwt_required()
def delete_listing(listing_type, listing_id):
    """
    Suppression générique d'une annonce.
    """
    try:
        user_id = int(get_jwt_identity())

        print(
            f"🗑️ DELETE LISTING - type={listing_type}, "
            f"id={listing_id}, user={user_id}"
        )

        # ----------------------------------------------------
        # PROPERTY
        # ----------------------------------------------------
        if listing_type == "property":
            item = Property.query.get_or_404(listing_id)

            if int(item.seller_id) != user_id:
                return jsonify({"error": "Non autorisé"}), 403

            db.session.delete(item)
            db.session.commit()

            print(f"✅ Property {listing_id} supprimée")

            return jsonify({
                "message": "Propriété supprimée",
                "id": listing_id,
                "type": "property"
            }), 200

        # ----------------------------------------------------
        # MATERIAL
        # ----------------------------------------------------
        elif listing_type == "material":
            item = Material.query.get_or_404(listing_id)

            if int(item.seller_id) != user_id:
                return jsonify({"error": "Non autorisé"}), 403

            db.session.delete(item)
            db.session.commit()

            print(f"✅ Material {listing_id} supprimé")

            return jsonify({
                "message": "Matériau supprimé",
                "id": listing_id,
                "type": "material"
            }), 200

        # ----------------------------------------------------
        # SERVICE
        # ----------------------------------------------------
        elif listing_type == "service":
            item = Service.query.get_or_404(listing_id)

            if int(item.provider_id) != user_id:
                return jsonify({"error": "Non autorisé"}), 403

            db.session.delete(item)
            db.session.commit()

            print(f"✅ Service {listing_id} supprimé")

            return jsonify({
                "message": "Service supprimé",
                "id": listing_id,
                "type": "service"
            }), 200

        # ----------------------------------------------------
        # RENTAL
        # ----------------------------------------------------
        elif listing_type == "rental":
            item = Rental.query.get_or_404(listing_id)

            if int(item.owner_id) != user_id:
                return jsonify({"error": "Non autorisé"}), 403

            db.session.delete(item)
            db.session.commit()

            print(f"✅ Rental {listing_id} supprimée")

            return jsonify({
                "message": "Location supprimée",
                "id": listing_id,
                "type": "rental"
            }), 200

        else:
            return jsonify({
                "error": "Type d'annonce invalide"
            }), 400

    except Exception as e:
        db.session.rollback()

        print(f"❌ Erreur suppression annonce: {e}")

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500

# ============================================================
# PROPRIÉTÉS
# ============================================================
@app.route("/api/properties", methods=["GET"])
def list_properties():
    properties = Property.query.filter_by(is_published=True).order_by(Property.created_at.desc()).all()
    return jsonify([p.to_dict() for p in properties]), 200

@app.route("/api/properties/<int:property_id>", methods=["GET"])
@jwt_required()
@require_active_subscription
def get_property(property_id):
    prop = Property.query.get_or_404(property_id)
    return jsonify(prop.to_dict()), 200

@app.route("/api/properties", methods=["POST"])
@jwt_required()
@require_active_subscription
@require_seller
def create_property():
    try:
        user_id = get_jwt_identity()
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.form.to_dict()
            files = request.files.getlist('images')
        else:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Données JSON invalides"}), 400
            files = []
        
        required = ["title", "price", "location"]
        for field in required:
            value = data.get(field)
            if not value or value == 'undefined' or value == '':
                return jsonify({"error": f"Champ manquant: {field}"}), 400
        
        def clean_value(value):
            if value is None or value == '' or value == 'undefined':
                return None
            return value
        
        def clean_float(value):
            if value is None or value == '' or value == 'undefined':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        def clean_int(value):
            if value is None or value == '' or value == 'undefined':
                return 0
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        
        prop = Property(
            title=data["title"],
            description=clean_value(data.get("description")),
            property_type=clean_value(data.get("property_type")) or "house",
            price=clean_float(data["price"]) or 0,
            bedrooms=clean_int(data.get("bedrooms")),
            bathrooms=clean_int(data.get("bathrooms")),
            surface=clean_float(data.get("surface")),
            land_surface=clean_float(data.get("land_surface")),
            location=data["location"],
            latitude=clean_float(data.get("latitude")),
            longitude=clean_float(data.get("longitude")),
            seller_id=user_id,
            is_published=True,
            is_rental=data.get("is_rental") == 'true' or data.get("is_rental") == True,
            price_per_night=clean_float(data.get("price_per_night")),
            available_from=clean_value(data.get("available_from")),
            available_to=clean_value(data.get("available_to")),
            image_urls=[]
        )
        db.session.add(prop)
        db.session.commit()
        
        property_id = prop.id
        
        if files:
            image_urls = []
            for file in files:
                if file.filename == '':
                    continue
                url = upload_property_image(file, property_id)
                if url:
                    image_urls.append(url)
            
            if image_urls:
                prop.image_urls = image_urls
                db.session.commit()
        
        return jsonify(prop.to_dict()), 201
        
    except Exception as e:
        print(f"❌ Erreur création propriété: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/properties/<int:property_id>/images", methods=["POST"])
@jwt_required()
def upload_property_images(property_id):
    try:
        user_id = get_jwt_identity()
        prop = Property.query.get_or_404(property_id)
        
        if prop.seller_id != user_id:
            return jsonify({"error": "Non autorisé"}), 403
        
        if 'images' not in request.files:
            return jsonify({"error": "Aucune image"}), 400
        
        files = request.files.getlist('images')
        image_urls = prop.image_urls or []
        
        for file in files:
            if file.filename == '':
                continue
            url = upload_image(file, "imafia/properties")
            if url:
                image_urls.append(url)
        
        prop.image_urls = image_urls
        db.session.commit()
        
        return jsonify({"image_urls": image_urls}), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/properties/<int:property_id>", methods=["PUT"])
@jwt_required()
def update_property(property_id):
    try:
        user_id = get_jwt_identity()
        prop = Property.query.get_or_404(property_id)
        
        if prop.seller_id != user_id:
            return jsonify({"error": "Non autorisé"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données invalides"}), 400
        
        if 'title' in data:
            prop.title = data['title']
        if 'description' in data:
            prop.description = data['description']
        if 'price' in data:
            prop.price = float(data['price'])
        if 'location' in data:
            prop.location = data['location']
        if 'is_published' in data:
            prop.is_published = data['is_published']
        
        db.session.commit()
        return jsonify(prop.to_dict()), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/properties/<int:property_id>", methods=["DELETE"])
@jwt_required()
def delete_property(property_id):
    try:
        user_id = get_jwt_identity()
        prop = Property.query.get_or_404(property_id)
        
        if prop.seller_id != user_id:
            return jsonify({"error": "Non autorisé"}), 403
        
        db.session.delete(prop)
        db.session.commit()
        return jsonify({"message": "Propriété supprimée"}), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================
# MATÉRIAUX
# ============================================================
@app.route("/api/materials", methods=["GET"])
def list_materials():
    materials = Material.query.filter_by(is_published=True).order_by(Material.created_at.desc()).all()
    return jsonify([m.to_dict() for m in materials]), 200


@app.route("/api/materials/<int:material_id>", methods=["GET"])
@jwt_required()
def get_material(material_id):
    material = Material.query.filter_by(
        id=material_id,
        is_published=True
    ).first()

    if not material:
        return jsonify({"error": "Matériau non trouvé"}), 404

    return jsonify(material.to_dict()), 200


@app.route("/api/materials", methods=["POST"])
@jwt_required()
@require_active_subscription
@require_seller
def create_material():
    try:
        user_id = get_jwt_identity()
        print(f"👤 Création matériau par user: {user_id}")
        print(f"📥 Content-Type: {request.content_type}")
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.form.to_dict()
            files = request.files.getlist('images')
            print(f"📸 Nombre d'images reçues: {len(files)}")
            print(f"📋 Données form: {data}")
        else:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Données invalides"}), 400
            files = []
            print(f"📋 Données JSON: {data}")
        
        required = ["title", "category", "price_per_unit", "quantity"]
        for field in required:
            value = data.get(field)
            if not value or value == 'undefined' or value == '':
                return jsonify({"error": f"Champ manquant: {field}"}), 400
        
        material = Material(
            title=data["title"],
            description=data.get("description"),
            category=data["category"],
            quantity=float(data["quantity"]),
            unit=data.get("unit", "pièce"),
            price_per_unit=float(data["price_per_unit"]),
            location=data.get("location"),
            seller_id=user_id,
            is_published=True,
            image_urls=[]
        )
        db.session.add(material)
        db.session.commit()
        
        material_id = material.id
        print(f"✅ Matériau créé avec l'ID: {material_id}")
        
        if files:
            from cloudinary_config import upload_material_image
            image_urls = []
            
            for file in files:
                if file.filename == '':
                    continue
                print(f"📤 Upload image: {file.filename}")
                url = upload_material_image(file, material_id)
                if url:
                    image_urls.append(url)
                    print(f"✅ Image uploadée: {url}")
                else:
                    print(f"❌ Échec upload: {file.filename}")
            
            if image_urls:
                material.image_urls = image_urls
                db.session.commit()
                print(f"✅ {len(image_urls)} images enregistrées")
        
        return jsonify(material.to_dict()), 201
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/materials/<int:material_id>/images", methods=["POST"])
@jwt_required()
def upload_material_images(material_id):
    try:
        user_id = get_jwt_identity()
        material = Material.query.get_or_404(material_id)
        
        if material.seller_id != user_id:
            return jsonify({"error": "Non autorisé"}), 403
        
        if 'images' not in request.files:
            return jsonify({"error": "Aucune image"}), 400
        
        files = request.files.getlist('images')
        image_urls = material.image_urls or []
        
        for file in files:
            if file.filename == '':
                continue
            url = upload_image(file, "imafia/materials")
            if url:
                image_urls.append(url)
        
        material.image_urls = image_urls
        db.session.commit()
        
        return jsonify({"message": f"{len(image_urls)} images uploadées", "image_urls": image_urls}), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/materials/<int:material_id>", methods=["PUT"])
@jwt_required()
def update_material(material_id):
    try:
        user_id = get_jwt_identity()
        material = Material.query.get_or_404(material_id)
        
        if material.seller_id != user_id:
            return jsonify({"error": "Non autorisé"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données invalides"}), 400
        
        if 'title' in data:
            material.title = data['title']
        if 'description' in data:
            material.description = data['description']
        if 'price_per_unit' in data:
            material.price_per_unit = float(data['price_per_unit'])
        if 'quantity' in data:
            material.quantity = float(data['quantity'])
        if 'is_published' in data:
            material.is_published = data['is_published']
        
        db.session.commit()
        return jsonify(material.to_dict()), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/materials/<int:material_id>", methods=["DELETE"])
@jwt_required()
def delete_material(material_id):
    try:
        user_id = get_jwt_identity()
        material = Material.query.get_or_404(material_id)
        
        if material.seller_id != user_id:
            return jsonify({"error": "Non autorisé"}), 403
        
        db.session.delete(material)
        db.session.commit()
        return jsonify({"message": "Matériau supprimé"}), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================
# SERVICES
# ============================================================


@app.route("/api/services", methods=["GET"])
def list_services():
    services = Service.query.filter_by(is_published=True).order_by(Service.created_at.desc()).all()
    return jsonify([s.to_dict() for s in services]), 200


@app.route("/api/services/<int:service_id>", methods=["GET"])
@jwt_required()
def get_service(service_id):
    service = Service.query.filter_by(
        id=service_id,
        is_published=True
    ).first()

    if not service:
        return jsonify({"error": "Service non trouvé"}), 404

    return jsonify(service.to_dict()), 200


@app.route("/api/services", methods=["POST"])
@jwt_required()
@require_active_subscription
@require_seller
def create_service():
    try:
        user_id = get_jwt_identity()
        print(f"👤 Création service par user: {user_id}")
        print(f"📥 Content-Type: {request.content_type}")
        
        # ✅ Vérifier si c'est du multipart/form-data (avec images)
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.form.to_dict()
            files = request.files.getlist('images')
            print(f"📸 Nombre d'images reçues: {len(files)}")
            print(f"📋 Données form: {data}")
        else:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Données invalides"}), 400
            files = []
            print(f"📋 Données JSON: {data}")
        
        required = ["title", "service_type"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": f"Champs manquants: {', '.join(missing)}"}), 400
        
        # ✅ Nettoyer les données
        def clean_value(value):
            if value is None or value == '' or value == 'undefined':
                return None
            return value
        
        def clean_float(value):
            if value is None or value == '' or value == 'undefined':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # ✅ Créer le service
        service = Service(
            title=data["title"],
            description=clean_value(data.get("description")),
            service_type=data["service_type"],
            price_estimate=clean_float(data.get("price_estimate")),
            location=clean_value(data.get("location")),
            provider_id=user_id,
            is_published=True,
            image_urls=[]
        )
        db.session.add(service)
        db.session.commit()
        
        service_id = service.id
        print(f"✅ Service créé avec l'ID: {service_id}")
        
        # ✅ Upload des images si présentes
        if files:
            from cloudinary_config import upload_image
            image_urls = []
            
            for file in files:
                if file.filename == '':
                    continue
                print(f"📤 Upload image: {file.filename}")
                url = upload_image(file, "imafia/services")
                if url:
                    image_urls.append(url)
                    print(f"✅ Image uploadée: {url}")
                else:
                    print(f"❌ Échec upload: {file.filename}")
            
            if image_urls:
                service.image_urls = image_urls
                db.session.commit()
                print(f"✅ {len(image_urls)} images enregistrées")
        
        return jsonify(service.to_dict()), 201
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/services/<int:service_id>/images", methods=["POST"])
@jwt_required()
def upload_service_images(service_id):
    try:
        user_id = get_jwt_identity()
        service = Service.query.get_or_404(service_id)
        
        if service.provider_id != user_id:
            return jsonify({"error": "Non autorisé"}), 403
        
        if 'images' not in request.files:
            return jsonify({"error": "Aucune image"}), 400
        
        files = request.files.getlist('images')
        image_urls = service.image_urls or []
        
        for file in files:
            if file.filename == '':
                continue
            url = upload_image(file, "imafia/services")
            if url:
                image_urls.append(url)
        
        service.image_urls = image_urls
        db.session.commit()
        
        return jsonify({"message": f"{len(image_urls)} images uploadées", "image_urls": image_urls}), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/services/<int:service_id>", methods=["PUT"])
@jwt_required()
def update_service(service_id):
    try:
        user_id = get_jwt_identity()
        service = Service.query.get_or_404(service_id)
        
        if service.provider_id != user_id:
            return jsonify({"error": "Non autorisé"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données invalides"}), 400
        
        if 'title' in data:
            service.title = data['title']
        if 'description' in data:
            service.description = data['description']
        if 'price_estimate' in data:
            service.price_estimate = float(data['price_estimate']) if data['price_estimate'] else None
        if 'is_published' in data:
            service.is_published = data['is_published']
        
        db.session.commit()
        return jsonify(service.to_dict()), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/services/<int:service_id>", methods=["DELETE"])
@jwt_required()
def delete_service(service_id):
    try:
        user_id = get_jwt_identity()
        service = Service.query.get_or_404(service_id)
        
        if service.provider_id != user_id:
            return jsonify({"error": "Non autorisé"}), 403
        
        db.session.delete(service)
        db.session.commit()
        return jsonify({"message": "Service supprimé"}), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500
# ============================================================
# LOCATIONS
# ============================================================
def parse_date(date_str):
    if not date_str:
        return None
    if '-' in date_str and len(date_str) == 10:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        pass
    try:
        return datetime.strptime(date_str, '%m/%d/%Y').date()
    except ValueError:
        pass
    return None

@app.route("/api/rentals", methods=["GET"])
def list_rentals():
    rentals = Rental.query.filter_by(is_published=True).order_by(Rental.created_at.desc()).all()
    return jsonify([r.to_dict() for r in rentals]), 200


@app.route("/api/rentals/<int:rental_id>", methods=["GET"])
@jwt_required()
def get_rental(rental_id):
    rental = Rental.query.filter_by(
        id=rental_id,
        is_published=True
    ).first()

    if not rental:
        return jsonify({"error": "Location non trouvée"}), 404

    return jsonify(rental.to_dict()), 200


@app.route("/api/rentals", methods=["POST"])
@jwt_required()
@require_active_subscription
@require_seller
def create_rental():
    try:
        user_id = get_jwt_identity()
        print(f"👤 Création location par user: {user_id}")
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.form.to_dict()
            files = request.files.getlist('images')
        else:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Données invalides"}), 400
            files = []
        
        required = ["title", "price_per_night", "location"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": f"Champs manquants: {', '.join(missing)}"}), 400
        
        available_from = parse_date(data.get("available_from"))
        available_to = parse_date(data.get("available_to"))
        
        rental = Rental(
            title=data["title"],
            description=data.get("description"),
            rental_type=data.get("rental_type", "room"),
            price_per_night=float(data["price_per_night"]),
            bedrooms=int(data.get("bedrooms", 1)),
            bathrooms=int(data.get("bathrooms", 1)),
            max_guests=int(data.get("max_guests", 2)),
            location=data["location"],
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            owner_id=user_id,
            amenities=data.get("amenities", []),
            available_from=available_from,
            available_to=available_to,
            is_published=True,
            image_urls=[]
        )
        db.session.add(rental)
        db.session.commit()
        
        print(f"✅ Location créée avec l'ID: {rental.id}, owner_id: {rental.owner_id}")
        
        if files:
            image_urls = []
            for file in files:
                if file.filename:
                    url = upload_image(file, "imafia/rentals")
                    if url:
                        image_urls.append(url)
            if image_urls:
                rental.image_urls = image_urls
                db.session.commit()
        
        return jsonify(rental.to_dict()), 201
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/rentals/<int:rental_id>/images", methods=["POST"])
@jwt_required()
def upload_rental_images(rental_id):
    try:
        user_id = get_jwt_identity()
        rental = Rental.query.get_or_404(rental_id)
        
        if rental.owner_id != user_id:
            return jsonify({"error": "Non autorisé"}), 403
        
        if 'images' not in request.files:
            return jsonify({"error": "Aucune image"}), 400
        
        files = request.files.getlist('images')
        image_urls = rental.image_urls or []
        
        for file in files:
            if file.filename == '':
                continue
            url = upload_image(file, "imafia/rentals")
            if url:
                image_urls.append(url)
        
        rental.image_urls = image_urls
        db.session.commit()
        
        return jsonify({"message": f"{len(image_urls)} images uploadées", "image_urls": image_urls}), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/rentals/<int:rental_id>", methods=["PUT"])
@jwt_required()
def update_rental(rental_id):
    try:
        user_id = get_jwt_identity()
        rental = Rental.query.get_or_404(rental_id)
        
        if rental.owner_id != user_id:
            return jsonify({"error": "Non autorisé"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données invalides"}), 400
        
        if 'title' in data:
            rental.title = data['title']
        if 'description' in data:
            rental.description = data['description']
        if 'price_per_night' in data:
            rental.price_per_night = float(data['price_per_night'])
        if 'is_published' in data:
            rental.is_published = data['is_published']
        if 'available_from' in data:
            rental.available_from = parse_date(data['available_from'])
        if 'available_to' in data:
            rental.available_to = parse_date(data['available_to'])
        
        db.session.commit()
        return jsonify(rental.to_dict()), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500

# backend/app.py - Ajouter dans delete_rental

@app.route("/api/rentals/<int:rental_id>", methods=["DELETE"])
@jwt_required()
def delete_rental(rental_id):
    try:
        user_id = get_jwt_identity()
        print(f"🔍 DELETE RENTAL - user_id: {user_id}, rental_id: {rental_id}")
        
        # ✅ Vérifier le token
        print(f"🔑 Token user: {user_id}")
        
        rental = Rental.query.get_or_404(rental_id)
        print(f"🛏️ Rental found: {rental.id} - {rental.title}")
        print(f"👤 Owner ID in DB: {rental.owner_id}")
        print(f"👤 Current user ID: {user_id}")
        print(f"🔍 Match: {rental.owner_id == user_id}")
        
        if rental.owner_id != user_id:
            print(f"❌ 403 - Non autorisé: {user_id} != {rental.owner_id}")
            return jsonify({"error": "Non autorisé"}), 403
        
        db.session.delete(rental)
        db.session.commit()
        print(f"✅ Location {rental_id} supprimée")
        return jsonify({"message": "Location supprimée"}), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    
@app.route("/api/admin/fix-rentals", methods=["POST"])
@jwt_required()
def fix_rentals():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.role != "admin":
            return jsonify({"error": "Admin requis"}), 403
        
        # ✅ Mettre à jour toutes les locations pour l'utilisateur 2
        rentals = Rental.query.filter(Rental.owner_id != 2).all()
        count = 0
        for rental in rentals:
            rental.owner_id = 2
            count += 1
        
        # ✅ Mettre à jour toutes les propriétés
        properties = Property.query.filter(Property.seller_id != 2).all()
        for prop in properties:
            prop.seller_id = 2
        
        # ✅ Mettre à jour tous les matériaux
        materials = Material.query.filter(Material.seller_id != 2).all()
        for mat in materials:
            mat.seller_id = 2
        
        # ✅ Mettre à jour tous les services
        services = Service.query.filter(Service.provider_id != 2).all()
        for serv in services:
            serv.provider_id = 2
        
        db.session.commit()
        
        return jsonify({
            "message": f"Correction effectuée: {count} locations, {len(properties)} propriétés, {len(materials)} matériaux, {len(services)} services"
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
# ============================================================
# PAIEMENTS GENIUS PAY
# ============================================================
@app.route("/api/payment/plans", methods=["GET"])
def get_plans():
    return jsonify(Config.PLANS), 200

@app.route("/api/payment/initiate", methods=["POST"])
@jwt_required()
def initiate_payment():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404
    
    data = request.get_json(silent=True) or {}
    plan_type = data.get("plan_type", "buyer")
    
    if plan_type == "seller":
        amount = Config.SELLER_PRICE
    else:
        amount = Config.BUYER_PRICE
    
    currency = data.get("currency", "XOF").upper()
    if currency not in ("XOF", "EUR", "USD"):
        currency = "XOF"
    
    try:
        result = create_genius_pay_payment(Config, amount, currency, user, plan_type)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"Impossible de contacter Genius Pay: {str(e)}"}), 502

@app.route("/api/payment/status/<reference>", methods=["GET"])
@jwt_required()
def payment_status(reference):
    user_id = get_jwt_identity()
    payment = Payment.query.filter_by(provider_reference=reference, user_id=user_id).first()
    
    if not payment:
        return jsonify({"error": "Paiement non trouvé"}), 404
    
    return jsonify({
        "status": payment.status,
        "amount": float(payment.amount),
        "created_at": payment.created_at.isoformat(),
        "subscription_days": payment.subscription_days
    }), 200

@app.route("/api/payment/confirm", methods=["POST"])
@jwt_required()
def confirm_payment():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404
    
    if user.account_status == "active" and user.subscription_expires and user.subscription_expires > datetime.utcnow():
        return jsonify({
            "message": "Abonnement déjà actif",
            "subscription": {"is_active": True, "expires_at": user.subscription_expires.isoformat()}
        }), 200
    
    payment = Payment.query.filter_by(user_id=user_id, status="completed").order_by(Payment.created_at.desc()).first()
    
    if payment:
        if activate_subscription(user, user.role or "seller"):
            return jsonify({"message": "Abonnement activé avec succès"}), 200
    
    if payment and payment.provider_reference:
        try:
            is_paid = verify_genius_pay_payment(Config, payment.provider_reference)
            if is_paid:
                payment.status = "completed"
                db.session.commit()
                if activate_subscription(user, user.role or "seller"):
                    return jsonify({"message": "Paiement confirmé, abonnement activé"}), 200
        except Exception as e:
            print(f"❌ Erreur vérification: {e}")
    
    return jsonify({"error": "Aucun paiement confirmé trouvé", "requires_subscription": True}), 402

@app.route("/api/payment/webhook", methods=["POST"])
def payment_webhook():
    raw_body = request.get_data()
    signature = request.headers.get("X-Webhook-Signature", "")
    timestamp = request.headers.get("X-Webhook-Timestamp", "")
    event = request.headers.get("X-Webhook-Event", "")
    
    if not verify_genius_pay_webhook_signature(Config, timestamp, raw_body, signature):
        log_payment_event(None, "unknown", "webhook_invalid_signature", "failed", raw_payload=raw_body.decode()[:500])
        return jsonify({"error": "Signature invalide"}), 401
    
    payload = request.get_json(silent=True) or {}
    transaction = payload.get("data", {})
    reference = transaction.get("reference")
    
    if not reference:
        return jsonify({"error": "Reference manquante"}), 400
    
    payment = Payment.query.filter_by(provider_reference=reference).first()
    if not payment:
        return jsonify({"error": "Paiement non trouvé"}), 404
    
    log_payment_event(payment.user_id, reference, event, transaction.get("status"), transaction.get("amount"), transaction.get("currency", "XOF"), raw_body.decode())
    
    if event == "payment.success" or transaction.get("status") == "completed":
        payment.status = "completed"
        payment.completed_at = datetime.utcnow()
        payment.provider_transaction_id = transaction.get("id")
        db.session.commit()
        
        user = User.query.get(payment.user_id)
        if user:
            plan_type = payment.payment_metadata.get("plan_type", "buyer") if payment.payment_metadata else "buyer"
            activate_subscription(user, plan_type)
    else:
        payment.status = "failed"
        payment.provider_transaction_id = transaction.get("id")
        db.session.commit()
    
    return jsonify({"received": True, "status": "processed"}), 200

@app.route("/api/payment/redirect", methods=["GET"])
def payment_redirect():
    status = request.args.get("status", "success")
    message = "✅ Paiement reçu ! Votre abonnement Imafia sera activé dans quelques instants." if status == "success" else "❌ Le paiement n'a pas abouti. Vous pouvez réessayer depuis l'application."
    emoji = "🎉" if status == "success" else "😅"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Imafia - Paiement</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #0D5CC9 0%, #1a7aeb 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                padding: 40px;
                max-width: 420px;
                width: 100%;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            .emoji {{ font-size: 72px; margin-bottom: 20px; }}
            .title {{ font-size: 28px; font-weight: bold; color: #0D5CC9; margin-bottom: 10px; }}
            .subtitle {{ font-size: 16px; color: #666; margin-bottom: 30px; line-height: 1.6; }}
            .button {{ display: inline-block; background: #0D5CC9; color: white; padding: 14px 40px; border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 16px; }}
            .button:hover {{ transform: scale(1.05); }}
            .footer {{ margin-top: 20px; font-size: 12px; color: #999; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="emoji">{emoji}</div>
            <div class="title">🏡 Imafia</div>
            <div class="subtitle">{message}</div>
            <a href="imafia://payment/status" class="button">Retourner à l'application</a>
            <div class="footer">Développé par Pythacademy • Assinie-Mafia</div>
        </div>
        <script>
            setTimeout(function() {{ window.location.href = "imafia://payment/status"; }}, 3000);
        </script>
    </body>
    </html>
    """

@app.route("/api/subscription/status", methods=["GET"])
@jwt_required()
def get_user_subscription_status():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        status = get_subscription_status(user)
        return jsonify(status), 200
    except Exception as e:
        print(f"❌ Erreur statut abonnement: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================
# HEALTH
# ============================================================
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "app": "Imafia API"}), 200



# ============================================================
# INIT
# ============================================================

with app.app_context():
    try:
        db.create_all()
        app.logger.info("Tables créées ou vérifiées.")

        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        app.logger.info("Tables PostgreSQL : %s", tables)

    except Exception:
        app.logger.exception("Erreur d'initialisation de la base de données")
        raise


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        debug=False,
        host="0.0.0.0",
        port=port
    )
