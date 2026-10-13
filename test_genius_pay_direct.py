# backend/test_genius_pay_direct.py
import requests
import json
from config import Config
import os

def test_genius_pay():
    print("🔧 Test direct Genius Pay...")
    print(f"URL: {Config.GENIUS_PAY_API_URL}")
    print(f"API Key: {Config.GENIUS_PAY_API_KEY[:10]}...")
    print(f"API Secret: {Config.GENIUS_PAY_API_SECRET[:10]}...")
    
    url = f"{Config.GENIUS_PAY_API_URL}/payments"
    
    headers = {
        "X-API-Key": Config.GENIUS_PAY_API_KEY,
        "X-API-Secret": Config.GENIUS_PAY_API_SECRET,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    payload = {
        "amount": 100,
        "currency": "XOF",
        "description": "Test Imafia",
        "customer": {
            "name": "Test User",
            "phone": "0700000000",
            "email": "test@imafia.com",
        },
        "success_url": "http://localhost:5000/api/payment/redirect",
        "error_url": "http://localhost:5000/api/payment/redirect",
        "metadata": {
            "test": "true"
        }
    }
    
    print(f"📤 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Response: {response.text[:500]}")
        
        if response.status_code in [200, 201]:
            print("✅ Test réussi !")
            data = response.json()
            print(f"📊 Data: {json.dumps(data, indent=2)}")
            return True
        else:
            print("❌ Test échoué")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    test_genius_pay()