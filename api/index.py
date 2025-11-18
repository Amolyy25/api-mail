#uvicorn envmail:app --reload
from pydantic import BaseModel, EmailStr
import smtplib
from email.message import EmailMessage
import os
from fastapi import Depends, Header, HTTPException
from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("API_KEY")

app = FastAPI(
    title="API Email Serenity Fitness",
    description="API pour l'envoi automatique d'emails",
    version="1.0.0"
)

def get_api_key(x_api_key: str = Header(None, alias="x-api-key")):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

async def send_excuse_to_user(email):
    """Envoie un email d'excuses à un utilisateur"""
    try:
        logger.info(f"📨 Envoi email d'excuses à : {email}")
        
        # Vérification de la configuration SMTP
        SMTP_SERVER = os.getenv("SMTP_SERVER")
        SMTP_PORT = os.getenv("SMTP_PORT", "465")
        SMTP_USER = os.getenv("SMTP_USER")
        SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        
        if not SMTP_PASSWORD or not SMTP_USER or not SMTP_SERVER:
            logger.error("❌ Configuration SMTP incomplète")
            raise HTTPException(status_code=500, detail="Configuration SMTP incomplète")
        
        try:
            SMTP_PORT = int(SMTP_PORT)
        except ValueError:
            SMTP_PORT = 465
        
        # Récupération des données utilisateur
        datadb = getclientbyid(email)
        if not datadb:
            logger.error(f"❌ Utilisateur introuvable pour : {email}")
            raise HTTPException(status_code=404, detail=f"Utilisateur introuvable")
        
        full_name = datadb.get("full_name", "Membre")
        
        # Préparation des variables pour le template
        variable = {"name": full_name}
        
        # Chargement du template HTML
        contenue_html = charger_template_html("excuses.html", variable)
        if not contenue_html:
            logger.error("❌ Template excuses.html non trouvé")
            raise HTTPException(status_code=500, detail="Template HTML non trouvé")
        
        # Création et envoi de l'email
        msg = EmailMessage()
        msg['Subject'] = "Message important - Serenity Fitness"
        msg['From'] = SMTP_USER
        msg['To'] = email
        msg.add_alternative(contenue_html, subtype="html")
        
        # Envoi via SMTP
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        
        logger.info(f"✅ Email d'excuses envoyé à {email}")
        return {"message": "succès", "email": email, "user": full_name}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'envoi à {email} : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur : {str(e)}")

@app.get("/")
async def root():
    return {"message": "API Email - Version 1.0.0", "status": "running"}

@app.get("/debug/test-supabase")
async def test_supabase(x_api_key: str = Depends(get_api_key)):
    """Endpoint de debug pour tester la connexion Supabase"""
    try:
        logger.info("🔍 Test de connexion Supabase...")
        
        # Test 1: Récupération des emails
        emails = getallemail()
        
        # Test 2: Si des emails existent, récupérer les infos du premier utilisateur
        test_results = {
            "supabase_connected": True,
            "total_users": len(emails),
            "emails_sample": emails[:10] if emails else [],
        }
        
        if emails:
            first_email = emails[3]
            user_data = getclientbyid(first_email)
            
            if user_data:
                user_id = user_data.get("id")
                test_results["test_user"] = {
                    "email": first_email,
                    "id": user_id,
                    "full_name": user_data.get("full_name")
                }
                
                # Test des stats
                stats = getsessionsbyid(user_id)
                test_results["test_user_stats"] = stats
                
                # Test des workouts de la semaine dernière
                workout_ids = get_workout_ids_last_week(user_id)
                seances_count = get_workouts_count_last_week(user_id)
                exercices_count = get_exercises_count_last_week(user_id)
                reps_total, reps_by_ex = get_total_reps_last_week(user_id)
                
                test_results["test_user_workouts_last_week"] = {
                    "workout_ids": workout_ids,
                    "seances_count": seances_count,
                    "exercices_count": exercices_count,
                    "total_reps": reps_total,
                    "exercises_detail": reps_by_ex
                }
        
        logger.info("✅ Test Supabase réussi")
        return test_results
        
    except Exception as e:
        logger.error(f"❌ Erreur test Supabase : {str(e)}")
        logger.exception("Stack trace complète :")
        return {
            "supabase_connected": False,
            "error": str(e)
        }

@app.post("/send-excuse-email")
async def send_excuse_email(x_api_key: str = Depends(get_api_key)):
    """Endpoint pour envoyer un email d'excuses à tous les utilisateurs"""
    logger.info("\n" + "📧"*30)
    logger.info("📧 ENVOI DES EMAILS D'EXCUSES")
    logger.info("📧"*30 + "\n")
    
    try: 
        emails = getallemail()
        
        if not emails:
            logger.warning("⚠️ Aucun email trouvé dans la base de données")
            return {
                "success": False, 
                "message": "Aucun email trouvé",
                "sent": 0,
                "failed": 0
            }
        
        logger.info(f"📬 {len(emails)} emails d'excuses à envoyer")
        
        sent_count = 0
        failed_count = 0
        failed_emails = []
        
        for email in emails:
            try:
                await send_excuse_to_user(email)
                sent_count += 1
            except Exception as e:
                failed_count += 1
                failed_emails.append({"email": email, "error": str(e)})
                logger.error(f"❌ Échec pour {email} : {str(e)}")
        
        logger.info("\n" + "="*60)
        logger.info(f"📊 RÉSUMÉ DE L'ENVOI D'EXCUSES")
        logger.info(f"✅ Envoyés avec succès : {sent_count}/{len(emails)}")
        logger.info(f"❌ Échecs : {failed_count}/{len(emails)}")
        logger.info("="*60 + "\n")
        
        return {
            "success": True,
            "message": f"Envoi terminé : {sent_count} succès, {failed_count} échecs",
            "sent": sent_count,
            "failed": failed_count,
            "total": len(emails),
            "failed_emails": failed_emails if failed_emails else []
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur fatale dans send_excuse_email : {str(e)}")
        logger.exception("Stack trace complète :")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur inattendue : {str(e)}"
        )

@app.post("/send-weekly-email")
async def send_weekly_email(x_api_key: str = Depends(get_api_key)):
    """Endpoint pour envoyer les emails hebdomadaires à tous les utilisateurs"""
    logger.info("\n" + "🚀"*30)
    logger.info("🚀 DÉMARRAGE DE L'ENVOI DES EMAILS HEBDOMADAIRES")
    logger.info("🚀"*30 + "\n")
    
    try: 
        emails = ["meiller.amaury@gmail.com"]
        
        if not emails:
            logger.warning("⚠️ Aucun email trouvé dans la base de données")
            return {
                "success": False, 
                "message": "Aucun email trouvé",
                "sent": 0,
                "failed": 0
            }
        
        logger.info(f"📬 {len(emails)} emails à envoyer")
        
        # Compteurs pour le résumé
        sent_count = 0
        failed_count = 0
        failed_emails = []
        
        for email in emails:
            try:
                await envmail(email)
                sent_count += 1
            except Exception as e:
                failed_count += 1
                failed_emails.append({"email": email, "error": str(e)})
                logger.error(f"❌ Échec pour {email} : {str(e)}")
        
        logger.info("\n" + "="*60)
        logger.info(f"📊 RÉSUMÉ DE L'ENVOI")
        logger.info(f"✅ Envoyés avec succès : {sent_count}/{len(emails)}")
        logger.info(f"❌ Échecs : {failed_count}/{len(emails)}")
        logger.info("="*60 + "\n")
        
        return {
            "success": True,
            "message": f"Envoi terminé : {sent_count} succès, {failed_count} échecs",
            "sent": sent_count,
            "failed": failed_count,
            "total": len(emails),
            "failed_emails": failed_emails if failed_emails else []
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur fatale dans send_weekly_email : {str(e)}")
        logger.exception("Stack trace complète :")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur inattendue : {str(e)}"
        )




url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

def getallemail():
    """Récupère tous les emails des utilisateurs"""
    try:
        logger.info("📧 Récupération de tous les emails...")
        responses = supabase.table('users').select('email').execute()
        emails = [row['email'] for row in (responses.data or []) if row.get('email')]
        logger.info(f"✅ {len(emails)} emails récupérés")
        return emails
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des emails : {str(e)}")
        return []


def getclientbyid(email):
    """Récupère les informations d'un utilisateur par son email"""
    try:
        logger.info(f"👤 Récupération des infos pour : {email}")
        responses = supabase.table('users').select('id, full_name, email').eq('email', email).execute()
        
        if responses.data and len(responses.data) > 0:
            user = responses.data[0]
            logger.info(f"✅ Utilisateur trouvé : {user.get('full_name')} (ID: {user.get('id')})")
            return user
        
        logger.warning(f"⚠️ Aucun utilisateur trouvé pour : {email}")
        return None
    except Exception as e:
        logger.error(f"❌ Erreur getclientbyid pour {email} : {str(e)}")
        return None

def getsessionsbyid(user_id):
    """Récupère les statistiques d'entraînement d'un utilisateur par son ID"""
    try:
        logger.info(f"📊 Récupération des stats pour user_id : {user_id}")
        # Correction : utilisation de user_id au lieu de email
        responses = supabase.table('user_workout_stats').select('total_workouts, total_exercises, last_workout_date, user_id').eq('user_id', user_id).execute()
        
        if responses.data and len(responses.data) > 0:
            stats = responses.data[0]
            logger.info(f"✅ Stats trouvées : {stats.get('total_workouts')} séances, {stats.get('total_exercises')} exercices")
            return stats
        
        logger.warning(f"⚠️ Aucune statistique trouvée pour user_id : {user_id}")
        # Retourner des valeurs par défaut au lieu de None
        return {
            'total_workouts': 0,
            'total_exercises': 0,
            'last_workout_date': 'Aucune séance'
        }
    except Exception as e:
        logger.error(f"❌ Erreur getsessionsbyid pour user_id {user_id} : {str(e)}")
        # Retourner des valeurs par défaut en cas d'erreur
        return {
            'total_workouts': 0,
            'total_exercises': 0,
            'last_workout_date': 'Erreur de chargement'
        }

def week_bounds_previous():
    """Calcule les bornes de la semaine précédente"""
    now = datetime.now(timezone.utc)
    start_curr_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start_prev_week = start_curr_week - timedelta(days=7)
    # Intervalle fermé/ouvert: [start_prev_week, start_curr_week)
    logger.info(f"📅 Période calculée : {start_prev_week.date()} à {start_curr_week.date()}")
    return start_prev_week.isoformat(), start_curr_week.isoformat()

def get_workout_ids_last_week(user_id: str):
    """Récupère les IDs des workouts de la semaine dernière pour un utilisateur"""
    try:
        start_prev, start_curr = week_bounds_previous()
        logger.info(f"🏋️ Recherche des workouts pour user_id {user_id} entre {start_prev} et {start_curr}")
        
        r = supabase.table('workouts') \
            .select('id, created_at') \
            .eq('user_id', user_id) \
            .gte('created_at', start_prev) \
            .lt('created_at', start_curr) \
            .execute()
        
        workout_ids = [row['id'] for row in (r.data or [])]
        logger.info(f"✅ {len(workout_ids)} workouts trouvés : {workout_ids}")
        return workout_ids
    except Exception as e:
        logger.error(f"❌ Erreur get_workout_ids_last_week pour user_id {user_id} : {str(e)}")
        return []

def get_workouts_count_last_week(user_id: str):
    """Compte le nombre de séances de la semaine dernière"""
    try:
        workout_ids = get_workout_ids_last_week(user_id)
        count = len(workout_ids)
        logger.info(f"📊 Nombre de séances la semaine dernière : {count}")
        return count
    except Exception as e:
        logger.error(f"❌ Erreur get_workouts_count_last_week pour user_id {user_id} : {str(e)}")
        return 0

def get_exercises_count_last_week(user_id: str):
    """Compte le nombre d'exercices distincts de la semaine dernière"""
    try:
        workout_ids = get_workout_ids_last_week(user_id)
        if not workout_ids:
            logger.warning(f"⚠️ Aucun workout pour compter les exercices")
            return 0
        
        r = supabase.table('exercises') \
            .select('name') \
            .in_('workout_id', workout_ids) \
            .execute()
        
        # Compter le nombre total d'exercices (pas distincts, mais tous les exercices faits)
        count = len(r.data) if r.data else 0
        logger.info(f"💪 Nombre d'exercices la semaine dernière : {count}")
        return count
    except Exception as e:
        logger.error(f"❌ Erreur get_exercises_count_last_week pour user_id {user_id} : {str(e)}")
        return 0

def get_total_reps_last_week(user_id: str):
    """Calcule le total de répétitions de la semaine dernière"""
    try:
        workout_ids = get_workout_ids_last_week(user_id)
        if not workout_ids:
            logger.warning(f"⚠️ Aucun workout trouvé pour user_id {user_id}")
            return 0, {}
        
        logger.info(f"💪 Recherche des exercices pour les workouts : {workout_ids}")
        r = supabase.table('exercises') \
            .select('name, reps, workout_id') \
            .in_('workout_id', workout_ids) \
            .execute()
        
        total = 0
        by_ex = {}
        
        if r.data:
            for row in r.data:
                reps = row.get('reps') or 0
                total += reps
                name = row.get('name') or 'Inconnu'
                by_ex[name] = by_ex.get(name, 0) + reps
            
            logger.info(f"✅ Total répétitions : {total}, Exercices : {len(by_ex)}")
        else:
            logger.warning(f"⚠️ Aucun exercice trouvé pour les workouts")
        
        return total, by_ex
    except Exception as e:
        logger.error(f"❌ Erreur get_total_reps_last_week pour user_id {user_id} : {str(e)}")
        return 0, {}

def charger_template_html(nom_fichier, variables=None):
    """Charge un template HTML et remplace les variables"""
    try:
        chemin_template = os.path.join("templates", nom_fichier)
        with open(chemin_template, 'r', encoding='utf-8') as fichier:
            contenu_html = fichier.read()
        
        if variables:
            for cle, valeur in variables.items():
                contenu_html = contenu_html.replace(f"{{{cle}}}", str(valeur))
        
        return contenu_html
    except FileNotFoundError:
        print(f"❌ Template {nom_fichier} non trouvé")
        return None


async def envmail(email):
    """Envoie un email récapitulatif à un utilisateur"""
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"📨 DÉBUT DE L'ENVOI D'EMAIL POUR : {email}")
        logger.info(f"{'='*60}")
        
        # Vérification de la configuration SMTP
        SMTP_SERVER = os.getenv("SMTP_SERVER")
        SMTP_PORT = os.getenv("SMTP_PORT", "465")  # Par défaut 465 pour SSL
        SMTP_USER = os.getenv("SMTP_USER")
        SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        
        if not SMTP_PASSWORD or not SMTP_USER or not SMTP_SERVER:
            logger.error("❌ Configuration SMTP incomplète")
            raise HTTPException(
                status_code=500, 
                detail="Configuration SMTP incomplète"
            )
        
        # Conversion du port en entier
        try:
            SMTP_PORT = int(SMTP_PORT)
        except ValueError:
            logger.error(f"❌ Port SMTP invalide : {SMTP_PORT}")
            SMTP_PORT = 465
        
        logger.info(f"🔧 Config SMTP : {SMTP_SERVER}:{SMTP_PORT}")
        
        # 1. Récupération des données utilisateur
        datadb = getclientbyid(email)
        if not datadb:
            logger.error(f"❌ Utilisateur introuvable pour : {email}")
            raise HTTPException(
                status_code=404, 
                detail=f"Utilisateur introuvable pour l'email : {email}"
            )
        
        user_id = datadb.get("id")
        full_name = datadb.get("full_name", "Utilisateur")
        
        if not user_id:
            logger.error(f"❌ user_id manquant pour : {email}")
            raise HTTPException(
                status_code=500, 
                detail="ID utilisateur manquant"
            )
        
        # 2. Récupération des statistiques GLOBALES (pour la dernière séance)
        datadb2 = getsessionsbyid(user_id)
        
        # 3. Calcul des statistiques de LA SEMAINE DERNIÈRE
        seances_semaine = get_workouts_count_last_week(user_id)
        exercices_semaine = get_exercises_count_last_week(user_id)
        repstotal_semaine, reps_par_exo = get_total_reps_last_week(user_id)
        
        logger.info(f"📈 Stats semaine dernière : {seances_semaine} séances, {exercices_semaine} exercices, {repstotal_semaine} reps")
        
        # 4. Préparation des variables pour le template
        variable = {
            "name": full_name,
            "seances": seances_semaine,  # CORRECTION : séances de la semaine dernière
            "last_workout_date": datadb2.get("last_workout_date", "Aucune séance"),
            "total_exercises": exercices_semaine,  # CORRECTION : exercices de la semaine dernière
            "repstotal": repstotal_semaine,  # Répétitions de la semaine dernière
        }
        
        logger.info(f"📝 Variables du template : {variable}")
        
        # 5. Chargement du template HTML
        contenue_html = charger_template_html("score.html", variable)
        if not contenue_html:
            logger.error("❌ Template HTML non trouvé")
            raise HTTPException(
                status_code=500, 
                detail="Template HTML non trouvé"
            )
        
        # 6. Création et envoi de l'email
        msg = EmailMessage()
        msg['Subject'] = "Votre récapitulatif de la semaine"
        msg['From'] = SMTP_USER
        msg['To'] = email
        msg.add_alternative(contenue_html, subtype="html")
        
        logger.info(f"📧 Envoi de l'email via {SMTP_SERVER}:{SMTP_PORT}...")
        
        # Utilisation de SMTP_SSL pour port 465, ou SMTP avec starttls pour port 587
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:  # Port 587
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        
        logger.info(f"✅ Email envoyé avec succès à {email}")
        logger.info(f"{'='*60}\n")
        return {
            "message": "succès",
            "email": email,
            "user": full_name
        }
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ Erreur d'authentification SMTP pour {email} : {str(e)}")
        raise HTTPException(
            status_code=401, 
            detail=f"Erreur d'authentification SMTP : {str(e)}"
        )
    except smtplib.SMTPException as e:
        logger.error(f"❌ Erreur SMTP pour {email} : {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur SMTP : {str(e)}"
        )
    except HTTPException:
        # Re-raise les HTTPException déjà gérées
        raise
    except Exception as e:
        logger.error(f"❌ Erreur inattendue pour {email} : {str(e)}")
        logger.exception("Stack trace complète :")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur inattendue : {str(e)}"
        )