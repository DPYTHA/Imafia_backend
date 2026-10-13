# backend/payments.py - Version exactement comme Admi.To
import requests
import hmac
import hashlib
import json
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================================
# GENIUS PAY - VERSION EXACTEMENT COMME ADMI.TO
# ============================================================================

def create_genius_pay_payment(config, amount, currency, user, plan_type="buyer"):
    """
    Crée une transaction Genius Pay - Version exactement comme Admi.To.
    """
    url = f"{config.GENIUS_PAY_API_URL}/payments"
    
    # ✅ Headers comme Admi.To
    headers = {
        "X-API-Key": config.GENIUS_PAY_API_KEY,
        "X-API-Secret": config.GENIUS_PAY_API_SECRET,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    # ✅ Récupérer le téléphone (comme Admi.To)
    customer_phone = getattr(user, 'telephone', '00000000')
    if not customer_phone or customer_phone == '00000000':
        customer_phone = '+2250710069791'  # ✅ Numéro par défaut comme Admi.To
    
    # ✅ Format international comme Admi.To
    if not customer_phone.startswith('+'):
        customer_phone = customer_phone.replace(' ', '').replace('-', '')
        if customer_phone.startswith('0'):
            customer_phone = '+225' + customer_phone[1:]
        else:
            customer_phone = '+225' + customer_phone
    
    # ✅ Payload exactement comme Admi.To
    payload = {
        "amount": int(amount),  # ✅ Montant en XOF
        "currency": currency,
        "description": f"Abonnement Imafia - {user.full_name}",
        "customer": {
            "name": user.full_name,
            "phone": customer_phone,  # ✅ Format +225...
            "email": f"{user.telephone}@imafia.com",
        },
        "success_url": config.GENIUS_PAY_REDIRECT_URL + "?status=success&user_id=" + str(user.id),
        "error_url": config.GENIUS_PAY_REDIRECT_URL + "?status=failed&user_id=" + str(user.id),
        "metadata": {
            "user_id": str(user.id),
            "plan_type": plan_type,
        }
    }

    print(f"💰 Paiement Genius Pay: {int(amount)} {currency}")
    print(f"   Utilisateur: {user.full_name} ({customer_phone})")
    print(f"   Plan: {plan_type}")

    try:
        response = requests.post(
            url, 
            json=payload,
            headers=headers, 
            timeout=30,
            verify=False  # ✅ Comme Admi.To
        )
        
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Response: {response.text[:500] if response.text else 'Vide'}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            result = data.get("data", data)
            
            return {
                "reference": result.get("reference"),
                "checkout_url": result.get("checkout_url") or result.get("payment_url"),
                "status": result.get("status"),
            }
        else:
            error_text = response.text if response.text else "Erreur inconnue"
            print(f"❌ Erreur: {error_text}")
            raise Exception(f"Genius Pay erreur {response.status_code}: {error_text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur Request: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"📄 Réponse: {e.response.text[:200]}")
        raise Exception(f"Impossible de contacter Genius Pay: {str(e)}")


def verify_genius_pay_payment(config, reference):
    """Vérifie le statut d'un paiement - Version Admi.To"""
    try:
        url = f"{config.GENIUS_PAY_API_URL}/payments/{reference}"
        headers = {
            "X-API-Key": config.GENIUS_PAY_API_KEY,
            "X-API-Secret": config.GENIUS_PAY_API_SECRET,
        }
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            result = data.get("data", data)
            status = result.get("status")
            print(f"🔍 Statut paiement: {status}")
            return status in ["completed", "success", "approved"]
        else:
            print(f"❌ Erreur vérification: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def verify_genius_pay_webhook_signature(config, timestamp, raw_body, signature_header):
    """Vérifie la signature du webhook - Version Admi.To"""
    if not config.GENIUS_PAY_WEBHOOK_SECRET or not signature_header or not timestamp:
        return False

    try:
        if abs(datetime.utcnow().timestamp() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False

    data_to_sign = f"{timestamp}.{raw_body.decode()}"
    expected_signature = hmac.new(
        config.GENIUS_PAY_WEBHOOK_SECRET.encode(),
        data_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)


def activate_subscription(user, plan_type="buyer"):
    """Active l'abonnement d'un utilisateur."""
    from models import db
    
    try:
        user.account_status = "active"
        user.subscription_expires = datetime.utcnow() + timedelta(days=30)
        
        if plan_type == "seller":
            user.role = "seller"
        else:
            user.role = "buyer"
        
        db.session.commit()
        print(f"✅ Abonnement activé pour {user.full_name} ({user.role})")
        return True
    except Exception as e:
        print(f"❌ Erreur activation: {e}")
        db.session.rollback()
        return False


def get_subscription_status(user):
    """Récupère le statut de l'abonnement d'un utilisateur."""
    if not user:
        return {"is_active": False, "expires_at": None, "days_left": 0}
    
    is_active = user.account_status == "active" and user.subscription_expires and user.subscription_expires > datetime.utcnow()
    
    if is_active:
        days_left = (user.subscription_expires - datetime.utcnow()).days
    else:
        days_left = 0
    
    return {
        "is_active": is_active,
        "expires_at": user.subscription_expires.isoformat() if user.subscription_expires else None,
        "days_left": days_left
    }


def log_payment_event(user_id, reference, event_type, status, amount=None, currency="XOF", raw_payload=None):
    """Journalise un événement de paiement."""
    try:
        from models import PaymentEvent
        
        event = PaymentEvent(
            user_id=user_id,
            provider="genius_pay",
            reference=reference,
            event_type=event_type,
            status=status,
            amount=amount,
            currency=currency,
            raw_payload=raw_payload
        )
        db.session.add(event)
        db.session.commit()
        print(f"📝 Événement journalisé: {event_type} - {reference}")
        return True
    except Exception as e:
        print(f"❌ Erreur journalisation: {e}")
        db.session.rollback()
        return False


def compute_next_period_end(days=30):
    """Calcule la date de fin de période d'abonnement."""
    return datetime.utcnow() + timedelta(days=days)