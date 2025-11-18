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
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

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

@app.post("/send-weekly-email")
async def send_weekly_email(x_api_key: str = Depends(get_api_key)):
    try: 
        emails = getallemail()
        for email in emails:
            await envmail(email)
        return {"success": True, "message": "Emails envoyé avec succès !"}
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=401, 
            detail="Erreur d'authentification SMTP - Vérifiez vos identifiants"
        )
    except smtplib.SMTPException as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur SMTP : {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur inattendue : {str(e)}"
        )





url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

def getallemail():
    responses = supabase.table('users').select('email').execute()
    return [row['email'] for row in (responses.data or [])]


def getclientbyid(email):
    try:
        responses = supabase.table('users').select('id, full_name').eq('email', email).execute()
        
        if responses.data:
            return responses.data[0]
        return None
    except Exception as e:
        return None

def getsessionsbyid(user_id):
    try:
        # Correction : utilisation de user_id au lieu de email
        responses = supabase.table('user_workout_stats').select('total_workouts, total_exercises, last_workout_date, user_id').eq('user_id', user_id).execute()
        
        if responses.data:
            return responses.data[0]
        return {
            'total_workouts': 0,
            'total_exercises': 0,
            'last_workout_date': 'Aucune séance'
        }
    except Exception as e:
        return {
            'total_workouts': 0,
            'total_exercises': 0,
            'last_workout_date': 'Erreur de chargement'
        }

from datetime import datetime, timedelta, timezone

def week_bounds_previous():
    now = datetime.now(timezone.utc)
    start_curr_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start_prev_week = start_curr_week - timedelta(days=7)
    # Intervalle fermé/ouvert: [start_prev_week, start_curr_week)
    return start_prev_week.isoformat(), start_curr_week.isoformat()

def get_workout_ids_last_week(user_id: str):
    start_prev, start_curr = week_bounds_previous()
    r = supabase.table('workouts') \
        .select('id') \
        .eq('user_id', user_id) \
        .gte('created_at', start_prev) \
        .lt('created_at', start_curr) \
        .execute()
    return [row['id'] for row in (r.data or [])]

def get_workouts_count_last_week(user_id: str):
    """Compte le nombre de séances de la semaine dernière"""
    workout_ids = get_workout_ids_last_week(user_id)
    return len(workout_ids)

def get_exercises_count_last_week(user_id: str):
    """Compte le nombre d'exercices de la semaine dernière"""
    workout_ids = get_workout_ids_last_week(user_id)
    if not workout_ids:
        return 0
    r = supabase.table('exercises') \
        .select('name') \
        .in_('workout_id', workout_ids) \
        .execute()
    return len(r.data) if r.data else 0

def get_total_reps_last_week(user_id: str):
    workout_ids = get_workout_ids_last_week(user_id)
    if not workout_ids:
        return 0, {}
    r = supabase.table('exercises') \
        .select('name ,reps,workout_id') \
        .in_('workout_id', workout_ids) \
        .execute()
    total = 0
    by_ex = {}
    for row in (r.data or []):
        reps = row.get('reps') or 0
        total += reps
        name = row.get('name') or 'Inconnu'
        by_ex[name] = by_ex.get(name, 0) + reps
    return total, by_ex

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
    try:
        SMTP_SERVER = os.getenv("SMTP_SERVER")
        SMTP_PORT = int(os.getenv("SMTP_PORT"))
        SMTP_USER = os.getenv("SMTP_USER")
        SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        if not SMTP_PASSWORD:
            raise HTTPException(
                status_code=500, 
                detail="Configuration SMTP incomplète : mot de passe manquant"
            )
        datadb = getclientbyid(email)
        if not datadb:
            raise HTTPException(status_code=404, detail=f"Utilisateur introuvable pour l'email : {email}")
        
        user_id = datadb.get("id")
        if not user_id:
            raise HTTPException(status_code=500, detail="ID utilisateur manquant")
        
        # Récupération des statistiques GLOBALES (pour la dernière séance)
        datadb2 = getsessionsbyid(user_id)
        
        # Calcul des statistiques de LA SEMAINE DERNIÈRE
        seances_semaine = get_workouts_count_last_week(user_id)
        exercices_semaine = get_exercises_count_last_week(user_id)
        repstotal_semaine, reps_par_exo = get_total_reps_last_week(user_id)
        
        print(f"Stats semaine : {seances_semaine} séances, {exercices_semaine} exercices, {repstotal_semaine} reps")
        
        variable = {
            "name": datadb.get("full_name", "Utilisateur"),
            "seances": seances_semaine,  # CORRECTION : séances de la semaine dernière
            "last_workout_date": datadb2.get("last_workout_date", "Aucune séance"),
            "total_exercises": exercices_semaine,  # CORRECTION : exercices de la semaine dernière
            "repstotal": repstotal_semaine,  # Répétitions de la semaine dernière
        }
        contenue_html = charger_template_html("score.html", variable)
        if not contenue_html:
            return {"error" : "Aucune template"}
        msg = EmailMessage()
        msg['Subject'] = "Votre récapitulatif de la semaine"
        msg['From'] = SMTP_USER
        msg['To'] = email
        msg.add_alternative(contenue_html, subtype="html")

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print("Le message c'est envoyé.")
        return {
            "message": "succès"
        }
    except smtplib.SMTPAuthenticationError:
        print("Le message ne c'est pas envoyé erreur d'id")
        raise HTTPException(
            status_code=401, 
            detail="Erreur d'authentification SMTP - Vérifiez vos identifiants"
        )
    except smtplib.SMTPException as e:
        print("erreur 500")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur SMTP : {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur inattendue : {str(e)}"
        )

