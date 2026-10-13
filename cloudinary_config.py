# backend/cloudinary_config.py
import cloudinary
import cloudinary.uploader
import cloudinary.api
from config import Config
import os
import base64
from datetime import datetime

# Configuration Cloudinary
print(f"🔧 Configuration Cloudinary:")
print(f"   Cloud Name: {Config.CLOUDINARY_CLOUD_NAME}")
print(f"   API Key: {Config.CLOUDINARY_API_KEY[:10] if Config.CLOUDINARY_API_KEY else 'NON DÉFINIE'}...")
print(f"   API Secret: {'✅ DÉFINI' if Config.CLOUDINARY_API_SECRET else 'NON DÉFINIE'}")

cloudinary.config(
    cloud_name=Config.CLOUDINARY_CLOUD_NAME,
    api_key=Config.CLOUDINARY_API_KEY,
    api_secret=Config.CLOUDINARY_API_SECRET,
    secure=True
)

def upload_image(file, folder="imafia", public_id=None):
    """
    Upload une image vers Cloudinary
    
    Args:
        file: Fichier à uploader (FileStorage ou chemin)
        folder: Dossier de destination dans Cloudinary
        public_id: ID public personnalisé (optionnel)
    
    Returns:
        str: URL sécurisée de l'image ou None en cas d'erreur
    """
    try:
        print(f"📤 Upload vers Cloudinary: {folder}")
        
        # Gérer les différents types d'entrée
        if hasattr(file, 'read'):
            # C'est un objet FileStorage
            if hasattr(file, 'seek'):
                file.seek(0)
            
            # Lire le contenu
            content = file.read()
            
            # Réinitialiser le pointeur pour une éventuelle réutilisation
            if hasattr(file, 'seek'):
                file.seek(0)
            
            # Paramètres d'upload
            upload_params = {
                "folder": folder,
                "resource_type": "image",
                "allowed_formats": ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']
            }
            
            if public_id:
                upload_params["public_id"] = public_id
                upload_params["overwrite"] = True
            
            result = cloudinary.uploader.upload(content, **upload_params)
            
            secure_url = result.get("secure_url")
            print(f"✅ Upload réussi: {secure_url}")
            return secure_url
            
        else:
            # C'est déjà une URL ou un chemin
            upload_params = {
                "folder": folder,
                "resource_type": "image"
            }
            
            if public_id:
                upload_params["public_id"] = public_id
                upload_params["overwrite"] = True
            
            result = cloudinary.uploader.upload(file, **upload_params)
            return result.get("secure_url")
            
    except Exception as e:
        print(f"❌ Erreur upload: {e}")
        import traceback
        traceback.print_exc()
        return None

def upload_property_image(file, property_id):
    """
    Upload une image de propriété vers Cloudinary
    """
    try:
        print(f"📤 Upload image propriété {property_id}")
        
        public_id = f"property_{property_id}_{datetime.utcnow().timestamp()}"
        
        if hasattr(file, 'read'):
            if hasattr(file, 'seek'):
                file.seek(0)
            
            result = cloudinary.uploader.upload(
                file,
                folder="imafia/properties",
                public_id=public_id,
                transformation={
                    "width": 800,
                    "height": 600,
                    "crop": "fill",
                    "quality": "auto:good"
                },
                resource_type="image",
                overwrite=True
            )
            
            secure_url = result.get("secure_url")
            print(f"✅ Image uploadée: {secure_url}")
            return secure_url
        return None
            
    except Exception as e:
        print(f"❌ Erreur upload: {e}")
        import traceback
        traceback.print_exc()
        return None

# backend/cloudinary_config.py - Ajouter cette fonction

def upload_property_image(file, property_id):
    """
    Upload une image de propriété vers Cloudinary avec transformation
    
    Args:
        file: Fichier à uploader
        property_id: ID de la propriété pour nommer le fichier
    
    Returns:
        str: URL sécurisée de l'image ou None en cas d'erreur
    """
    try:
        print(f"📤 Upload image propriété {property_id}")
        
        # Générer un nom unique
        public_id = f"property_{property_id}_{datetime.utcnow().timestamp()}"
        
        if hasattr(file, 'read'):
            if hasattr(file, 'seek'):
                file.seek(0)
            
            content = file.read()
            
            if hasattr(file, 'seek'):
                file.seek(0)
            
            # Upload avec transformation pour optimiser l'affichage
            result = cloudinary.uploader.upload(
                content,
                folder="imafia/properties",
                public_id=public_id,
                transformation={
                    "width": 800,
                    "height": 600,
                    "crop": "fill",
                    "quality": "auto:good"
                },
                resource_type="image",
                overwrite=True
            )
            
            secure_url = result.get("secure_url")
            print(f"✅ Image uploadée: {secure_url}")
            return secure_url
            
        else:
            result = cloudinary.uploader.upload(
                file,
                folder="imafia/properties",
                public_id=public_id,
                transformation={
                    "width": 800,
                    "height": 600,
                    "crop": "fill",
                    "quality": "auto:good"
                },
                overwrite=True
            )
            return result.get("secure_url")
            
    except Exception as e:
        print(f"❌ Erreur upload image propriété: {e}")
        import traceback
        traceback.print_exc()
        return None

# backend/cloudinary_config.py - Ajouter ces fonctions

def upload_material_image(file, material_id):
    """
    Upload une image de matériau vers Cloudinary
    """
    try:
        print(f"📤 Upload image matériau {material_id}")
        
        public_id = f"material_{material_id}_{datetime.utcnow().timestamp()}"
        
        if hasattr(file, 'read'):
            if hasattr(file, 'seek'):
                file.seek(0)
            
            result = cloudinary.uploader.upload(
                file,
                folder="imafia/materials",
                public_id=public_id,
                transformation={
                    "width": 800,
                    "height": 600,
                    "crop": "fill",
                    "quality": "auto:good"
                },
                resource_type="image",
                overwrite=True
            )
            
            secure_url = result.get("secure_url")
            print(f"✅ Image uploadée: {secure_url}")
            return secure_url
        return None
            
    except Exception as e:
        print(f"❌ Erreur upload: {e}")
        import traceback
        traceback.print_exc()
        return None

def upload_service_image(file, service_id):
    """
    Upload une image de service vers Cloudinary
    """
    try:
        print(f"📤 Upload image service {service_id}")
        
        public_id = f"service_{service_id}_{datetime.utcnow().timestamp()}"
        
        if hasattr(file, 'read'):
            if hasattr(file, 'seek'):
                file.seek(0)
            
            result = cloudinary.uploader.upload(
                file,
                folder="imafia/services",
                public_id=public_id,
                transformation={
                    "width": 800,
                    "height": 600,
                    "crop": "fill",
                    "quality": "auto:good"
                },
                resource_type="image",
                overwrite=True
            )
            
            secure_url = result.get("secure_url")
            print(f"✅ Image uploadée: {secure_url}")
            return secure_url
        return None
            
    except Exception as e:
        print(f"❌ Erreur upload: {e}")
        import traceback
        traceback.print_exc()
        return None

def upload_rental_image(file, rental_id):
    """
    Upload une image de location vers Cloudinary
    """
    try:
        print(f"📤 Upload image location {rental_id}")
        
        public_id = f"rental_{rental_id}_{datetime.utcnow().timestamp()}"
        
        if hasattr(file, 'read'):
            if hasattr(file, 'seek'):
                file.seek(0)
            
            result = cloudinary.uploader.upload(
                file,
                folder="imafia/rentals",
                public_id=public_id,
                transformation={
                    "width": 800,
                    "height": 600,
                    "crop": "fill",
                    "quality": "auto:good"
                },
                resource_type="image",
                overwrite=True
            )
            
            secure_url = result.get("secure_url")
            print(f"✅ Image uploadée: {secure_url}")
            return secure_url
        return None
            
    except Exception as e:
        print(f"❌ Erreur upload: {e}")
        import traceback
        traceback.print_exc()
        return None
    
def upload_avatar(file, user_id):
    """
    Upload un avatar vers Cloudinary avec transformation
    
    Args:
        file: Fichier à uploader
        user_id: ID de l'utilisateur pour nommer le fichier
    
    Returns:
        str: URL sécurisée de l'avatar ou None en cas d'erreur
    """
    try:
        print(f"📤 Upload avatar pour user {user_id}")
        
        public_id = f"user_{user_id}_{datetime.utcnow().timestamp()}"
        
        if hasattr(file, 'read'):
            if hasattr(file, 'seek'):
                file.seek(0)
            
            content = file.read()
            
            if hasattr(file, 'seek'):
                file.seek(0)
            
            result = cloudinary.uploader.upload(
                content,
                folder="imafia/avatars",
                public_id=public_id,
                transformation=[
                    {"width": 200, "height": 200, "crop": "fill", "gravity": "face"},
                    {"radius": "max"}  # Avatar rond
                ],
                resource_type="image",
                overwrite=True
            )
            
            secure_url = result.get("secure_url")
            print(f"✅ Avatar uploadé: {secure_url}")
            return secure_url
            
        else:
            result = cloudinary.uploader.upload(
                file,
                folder="imafia/avatars",
                public_id=public_id,
                transformation=[
                    {"width": 200, "height": 200, "crop": "fill", "gravity": "face"},
                    {"radius": "max"}
                ],
                overwrite=True
            )
            return result.get("secure_url")
            
    except Exception as e:
        print(f"❌ Erreur upload avatar: {e}")
        import traceback
        traceback.print_exc()
        return None

def delete_image(public_id):
    """
    Supprime une image de Cloudinary
    
    Args:
        public_id: ID public de l'image à supprimer
    
    Returns:
        bool: True si la suppression est réussie
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        print(f"🗑️ Image supprimée: {public_id}")
        return True
    except Exception as e:
        print(f"❌ Erreur suppression: {e}")
        return False

def get_image_url(public_id, transformations=None):
    """
    Génère une URL pour une image Cloudinary
    
    Args:
        public_id: ID public de l'image
        transformations: Transformations optionnelles (dict)
    
    Returns:
        str: URL de l'image
    """
    if not public_id:
        return None
    
    if transformations:
        url = cloudinary.CloudinaryImage(public_id).build_url(**transformations)
    else:
        url = cloudinary.CloudinaryImage(public_id).build_url()
    
    return url

def get_avatar_url(user_id, size=200):
    """
    Génère une URL d'avatar avec fallback
    
    Args:
        user_id: ID de l'utilisateur
        size: Taille de l'avatar
    
    Returns:
        str: URL de l'avatar
    """
    public_id = f"imafia/avatars/user_{user_id}"
    
    try:
        # Vérifier si l'avatar existe
        result = cloudinary.api.resource(public_id)
        return cloudinary.CloudinaryImage(public_id).build_url(
            width=size,
            height=size,
            crop="fill",
            gravity="face",
            radius="max"
        )
    except:
        # Retourner une URL de fallback si l'avatar n'existe pas
        return f"https://ui-avatars.com/api/?name=User&size={size}&background=0D5CC9&color=fff&bold=true"