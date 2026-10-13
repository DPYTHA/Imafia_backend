# backend/models.py - Version finale corrigée
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    telephone = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="buyer")
    account_status = db.Column(db.String(20), default="inactive")
    subscription_expires = db.Column(db.DateTime)
    avatar_url = db.Column(db.String(500))
    email = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    properties = db.relationship("Property", back_populates="seller", lazy=True)
    materials = db.relationship("Material", back_populates="seller", lazy=True)
    services = db.relationship("Service", back_populates="provider", lazy=True)
    rentals = db.relationship("Rental", back_populates="owner", lazy=True)
    payments = db.relationship("Payment", back_populates="user", lazy=True)
    favorites = db.relationship("Favorite", back_populates="user", lazy=True)  # ✅ Ajout
    
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())
    
    def to_dict(self):
        return {
            "id": self.id,
            "telephone": self.telephone,
            "full_name": self.full_name,
            "role": self.role,
            "account_status": self.account_status,
            "subscription_expires": self.subscription_expires.isoformat() if self.subscription_expires else None,
            "avatar_url": self.avatar_url,
            "email": self.email,
            "bio": self.bio,
            "location": self.location,
            "created_at": self.created_at.isoformat(),
        }


class Property(db.Model):
    __tablename__ = "properties"
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    property_type = db.Column(db.String(30), default="house")
    price = db.Column(db.Numeric(15, 0), nullable=False)
    bedrooms = db.Column(db.Integer, default=0)
    bathrooms = db.Column(db.Integer, default=0)
    surface = db.Column(db.Numeric(10, 2))
    land_surface = db.Column(db.Numeric(10, 2))
    location = db.Column(db.String(200))
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    image_urls = db.Column(db.JSON, default=list)
    is_published = db.Column(db.Boolean, default=False)
    is_rental = db.Column(db.Boolean, default=False)
    price_per_night = db.Column(db.Numeric(10, 0))
    available_from = db.Column(db.Date, nullable=True)  
    available_to = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    seller = db.relationship("User", back_populates="properties")
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "property_type": self.property_type,
            "price": float(self.price),
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "surface": float(self.surface) if self.surface else None,
            "land_surface": float(self.land_surface) if self.land_surface else None,
            "location": self.location,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "seller_id": self.seller_id,
            "seller_name": self.seller.full_name if self.seller else None,
            "seller_phone": self.seller.telephone if self.seller else None,
            "seller_avatar": self.seller.avatar_url if self.seller else None,
            "image_urls": self.image_urls or [],
            "is_published": self.is_published,
            "is_rental": self.is_rental,
            "price_per_night": float(self.price_per_night) if self.price_per_night else None,
            "available_from": self.available_from.isoformat() if self.available_from else None,
            "available_to": self.available_to.isoformat() if self.available_to else None,
            "created_at": self.created_at.isoformat(),
        }


class Material(db.Model):
    __tablename__ = "materials"
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Numeric(10, 2))
    unit = db.Column(db.String(20))
    price_per_unit = db.Column(db.Numeric(10, 0), nullable=False)
    location = db.Column(db.String(200))
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    image_urls = db.Column(db.JSON, default=list)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    seller = db.relationship("User", back_populates="materials")
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "quantity": float(self.quantity) if self.quantity else None,
            "unit": self.unit,
            "price_per_unit": float(self.price_per_unit),
            "location": self.location,
            "seller_id": self.seller_id,
            "seller_name": self.seller.full_name if self.seller else None,
            "seller_phone": self.seller.telephone if self.seller else None,
            "seller_avatar": self.seller.avatar_url if self.seller else None,
            "image_urls": self.image_urls or [],
            "is_published": self.is_published,
            "created_at": self.created_at.isoformat(),
        }


class Service(db.Model):
    __tablename__ = "services"
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    service_type = db.Column(db.String(50), nullable=False)
    price_estimate = db.Column(db.Numeric(10, 0))
    location = db.Column(db.String(200))
    provider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    image_urls = db.Column(db.JSON, default=list)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    provider = db.relationship("User", back_populates="services")
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "service_type": self.service_type,
            "price_estimate": float(self.price_estimate) if self.price_estimate else None,
            "location": self.location,
            "provider_id": self.provider_id,
            "provider_name": self.provider.full_name if self.provider else None,
            "provider_phone": self.provider.telephone if self.provider else None,
            "provider_avatar": self.provider.avatar_url if self.provider else None,
            "image_urls": self.image_urls or [],
            "is_published": self.is_published,
            "created_at": self.created_at.isoformat(),
        }


class Rental(db.Model):
    __tablename__ = "rentals"
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    rental_type = db.Column(db.String(30), default="room")
    price_per_night = db.Column(db.Numeric(10, 0), nullable=False)
    bedrooms = db.Column(db.Integer, default=1)
    bathrooms = db.Column(db.Integer, default=1)
    max_guests = db.Column(db.Integer, default=2)
    location = db.Column(db.String(200))
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    image_urls = db.Column(db.JSON, default=list)
    amenities = db.Column(db.JSON, default=list)
    available_from = db.Column(db.Date)
    available_to = db.Column(db.Date)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    owner = db.relationship("User", back_populates="rentals")
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "rental_type": self.rental_type,
            "price_per_night": float(self.price_per_night),
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "max_guests": self.max_guests,
            "location": self.location,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "owner_id": self.owner_id,
            "owner_name": self.owner.full_name if self.owner else None,
            "owner_phone": self.owner.telephone if self.owner else None,
            "owner_avatar": self.owner.avatar_url if self.owner else None,
            "image_urls": self.image_urls or [],
            "amenities": self.amenities or [],
            "available_from": self.available_from.isoformat() if self.available_from else None,
            "available_to": self.available_to.isoformat() if self.available_to else None,
            "is_published": self.is_published,
            "created_at": self.created_at.isoformat(),
        }


class Payment(db.Model):
    __tablename__ = "payments"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 0), nullable=False)
    provider = db.Column(db.String(20), default="genius_pay")
    provider_reference = db.Column(db.String(255))
    provider_transaction_id = db.Column(db.String(255))
    status = db.Column(db.String(20), default="pending")  # pending, completed, failed, expired
    subscription_days = db.Column(db.Integer, default=30)
    payment_metadata = db.Column(db.JSON, default={})
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", back_populates="payments")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": float(self.amount),
            "provider": self.provider,
            "provider_reference": self.provider_reference,
            "provider_transaction_id": self.provider_transaction_id,
            "status": self.status,
            "subscription_days": self.subscription_days,
            "payment_metadata": self.payment_metadata,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
        }


class PaymentEvent(db.Model):
    __tablename__ = "payment_events"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    provider = db.Column(db.String(20), default="genius_pay")
    reference = db.Column(db.String(255))
    event_type = db.Column(db.String(50))
    status = db.Column(db.String(20))
    amount = db.Column(db.Numeric(10, 0))
    currency = db.Column(db.String(3), default="XOF")
    raw_payload = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", backref="payment_events")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "reference": self.reference,
            "event_type": self.event_type,
            "status": self.status,
            "amount": float(self.amount) if self.amount else None,
            "currency": self.currency,
            "created_at": self.created_at.isoformat(),
        }


# ✅ NOUVEAU MODÈLE FAVORITES
class Favorite(db.Model):
    __tablename__ = "favorites"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    item_type = db.Column(db.String(20), nullable=False)  # property, material, service, rental
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", back_populates="favorites")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "item_id": self.item_id,
            "item_type": self.item_type,
            "created_at": self.created_at.isoformat(),
        }


# ✅ NOUVEAU MODÈLE NOTIFICATIONS
class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)

    # Utilisateur qui reçoit la notification
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Utilisateur à l'origine de la notification, si applicable
    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    type = db.Column(
        db.String(50),
        nullable=False,
        default="general"
    )

    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=True)

    read = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "actor_id": self.actor_id,
            "type": self.type,
            "title": self.title,
            "message": self.message or "",
            "read": bool(self.read),
            "created_at": (
                self.created_at.isoformat() + "Z"
                if self.created_at else None
            )
        }
