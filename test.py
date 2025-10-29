#!/usr/bin/env python3
"""Test direct de l'envoi d'email"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.email_service import EmailService

def test_direct():
    print("🧪 Test direct d'envoi email...")
    service = EmailService()
    
    success = service.send_email(
        to_email="soumare.birante05@gmail.com",
        subject="TEST DIRECT - From support@uzeur.com",
        body="Ceci est un test direct. Doit arriver de support@uzeur.com"
    )
    
    print(f"Résultat: {'✅ SUCCÈS' if success else '❌ ÉCHEC'}")

if __name__ == "__main__":
    test_direct()