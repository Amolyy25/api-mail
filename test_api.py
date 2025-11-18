"""
Script de test pour l'API Email Serenity Fitness
Usage: python test_api.py
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = "http://127.0.0.1:8000"  # URL locale
API_KEY = os.getenv("API_KEY")

def test_root():
    """Test de la route racine"""
    print("\n" + "="*60)
    print("🧪 TEST 1: Route racine GET /")
    print("="*60)
    
    response = requests.get(f"{API_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200
    print("✅ Test réussi!")

def test_debug_supabase():
    """Test de l'endpoint de debug Supabase"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Endpoint de debug GET /debug/test-supabase")
    print("="*60)
    
    headers = {"x-api-key": API_KEY}
    response = requests.get(f"{API_URL}/debug/test-supabase", headers=headers)
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    print("\n📊 Résultats:")
    print(f"  - Connexion Supabase: {data.get('supabase_connected')}")
    print(f"  - Nombre d'utilisateurs: {data.get('total_users')}")
    
    if data.get('test_user'):
        print(f"\n👤 Utilisateur de test:")
        print(f"  - Email: {data['test_user'].get('email')}")
        print(f"  - Nom: {data['test_user'].get('full_name')}")
        print(f"  - ID: {data['test_user'].get('id')}")
    
    if data.get('test_user_stats'):
        print(f"\n📈 Stats globales:")
        print(f"  - Total séances: {data['test_user_stats'].get('total_workouts')}")
        print(f"  - Total exercices: {data['test_user_stats'].get('total_exercises')}")
        print(f"  - Dernière séance: {data['test_user_stats'].get('last_workout_date')}")
    
    if data.get('test_user_workouts_last_week'):
        week_data = data['test_user_workouts_last_week']
        print(f"\n📅 Stats de la semaine dernière:")
        print(f"  - Séances: {week_data.get('seances_count')}")
        print(f"  - Exercices: {week_data.get('exercices_count')}")
        print(f"  - Répétitions totales: {week_data.get('total_reps')}")
        print(f"  - IDs des workouts: {week_data.get('workout_ids')}")
        
        if week_data.get('exercises_detail'):
            print(f"  - Détail par exercice:")
            for exercise, reps in week_data['exercises_detail'].items():
                print(f"    • {exercise}: {reps} reps")
    
    assert response.status_code == 200
    assert data.get('supabase_connected') == True
    print("\n✅ Test réussi!")

def test_send_email_without_key():
    """Test de l'envoi sans clé API (doit échouer)"""
    print("\n" + "="*60)
    print("🧪 TEST 3: Envoi d'email SANS clé API (doit échouer)")
    print("="*60)
    
    response = requests.post(f"{API_URL}/send-weekly-email")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 401
    print("✅ Test réussi! (Authentification refusée comme prévu)")

def test_send_email_with_key():
    """Test de l'envoi avec clé API"""
    print("\n" + "="*60)
    print("🧪 TEST 4: Envoi d'email AVEC clé API")
    print("="*60)
    print("⚠️  ATTENTION: Ceci va envoyer des emails réels!")
    
    confirm = input("Voulez-vous continuer? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Test annulé par l'utilisateur")
        return
    
    headers = {"x-api-key": API_KEY}
    response = requests.post(f"{API_URL}/send-weekly-email", headers=headers)
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"\n📊 Résultats:")
    print(f"  - Succès: {data.get('success')}")
    print(f"  - Message: {data.get('message')}")
    print(f"  - Envoyés: {data.get('sent')}")
    print(f"  - Échecs: {data.get('failed')}")
    print(f"  - Total: {data.get('total')}")
    
    if data.get('failed_emails'):
        print(f"\n❌ Emails en échec:")
        for failed in data['failed_emails']:
            print(f"  - {failed.get('email')}: {failed.get('error')}")
    
    assert response.status_code == 200
    print("\n✅ Test réussi!")

if __name__ == "__main__":
    print("\n" + "🚀"*30)
    print("🚀 TEST DE L'API EMAIL SERENITY FITNESS")
    print("🚀"*30)
    
    if not API_KEY:
        print("\n❌ ERREUR: Variable API_KEY non trouvée dans .env")
        exit(1)
    
    try:
        # Test 1: Route racine
        test_root()
        
        # Test 2: Debug Supabase
        test_debug_supabase()
        
        # Test 3: Sans clé API
        test_send_email_without_key()
        
        # Test 4: Avec clé API (optionnel)
        print("\n" + "-"*60)
        print("Test optionnel: Envoi d'emails réels")
        print("-"*60)
        test_send_email_with_key()
        
        print("\n" + "🎉"*30)
        print("🎉 TOUS LES TESTS SONT PASSÉS!")
        print("🎉"*30 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ Test échoué: {e}")
        exit(1)
    except requests.exceptions.ConnectionError:
        print("\n❌ ERREUR: Impossible de se connecter à l'API")
        print("Assurez-vous que le serveur est lancé avec:")
        print("  uvicorn api.index:app --reload")
        exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

