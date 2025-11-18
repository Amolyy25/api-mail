# 🔧 Corrections Apportées à l'API Email Serenity Fitness

## 📅 Date : 18 Novembre 2025

---

## 🔴 Problèmes Identifiés et Corrigés

### 1. **Erreur Critique : Mauvaises Données dans les Emails**

**Problème :**
- L'email affichait le **TOTAL** de toutes les séances au lieu des séances de **la semaine dernière**
- Même problème pour le nombre d'exercices

**Cause :**
- Les variables `seances` et `total_exercises` utilisaient les données de la table `user_workout_stats` qui contient les statistiques **globales** et non celles de la semaine dernière

**Solution :**
- Création de 2 nouvelles fonctions :
  - `get_workouts_count_last_week(user_id)` : Compte les séances de la semaine dernière
  - `get_exercises_count_last_week(user_id)` : Compte les exercices de la semaine dernière
- Modification de la fonction `envmail()` pour utiliser ces nouvelles fonctions

---

### 2. **Erreur de Requête Supabase**

**Problème :**
- La fonction `getsessionsbyid(email)` cherchait dans `user_workout_stats` avec un `email`
- Or, cette table utilise `user_id` comme clé étrangère, pas `email`

**Solution :**
- Changement de `getsessionsbyid(email)` → `getsessionsbyid(user_id)`
- La requête utilise maintenant `.eq('user_id', user_id)` au lieu de `.eq('email', email)`

---

### 3. **Gestion d'Erreurs Insuffisante**

**Problème :**
- Si `datadb` ou `datadb2` retournait `None`, le code plantait
- Pas de validation des données avant utilisation

**Solution :**
- Ajout de vérifications `if not datadb:` avec HTTPException appropriées
- Utilisation de `.get()` avec valeurs par défaut pour éviter les KeyError
- Retour de valeurs par défaut (0, "Aucune séance") au lieu de `None`

---

### 4. **Logs Insuffisants pour le Débogage**

**Problème :**
- Impossible de savoir où le code échouait
- Pas de trace des requêtes Supabase

**Solution :**
- Ajout d'un système de logging complet avec emojis
- Logs détaillés pour chaque requête Supabase
- Logs des erreurs avec stack trace complète
- Résumé visuel de l'envoi des emails

---

### 5. **Configuration SMTP Incorrecte**

**Problème :**
- Utilisation de `SMTP_SSL` avec le port 587 (qui nécessite `starttls`)
- Port 465 nécessite `SMTP_SSL`, port 587 nécessite `SMTP` avec `starttls`

**Solution :**
- Détection automatique du port
- Si port 465 → utilisation de `SMTP_SSL`
- Si port 587 → utilisation de `SMTP` avec `starttls()`

---

### 6. **Structure Vercel Incorrecte**

**Problème :**
- Erreur 404 Not Found sur Vercel
- Le code était dans `envmail.py` mais Vercel cherche dans `api/index.py`

**Solution :**
- Déplacement de tout le code vers `api/index.py`
- Création du fichier `vercel.json` pour la configuration
- Ajout d'une route racine `GET /`

---

## ✨ Nouvelles Fonctionnalités Ajoutées

### 1. **Endpoint de Debug**
```
GET /debug/test-supabase
Header: x-api-key: YOUR_API_KEY
```

Permet de tester :
- Connexion Supabase
- Récupération des utilisateurs
- Calcul des statistiques de la semaine dernière
- Détection des problèmes de données

### 2. **Meilleure Réponse de l'API**

L'endpoint `/send-weekly-email` retourne maintenant :
```json
{
  "success": true,
  "message": "Envoi terminé : 5 succès, 1 échecs",
  "sent": 5,
  "failed": 1,
  "total": 6,
  "failed_emails": [
    {
      "email": "user@example.com",
      "error": "Utilisateur introuvable"
    }
  ]
}
```

---

## 📊 Fonctions Ajoutées

### Nouvelles Fonctions de Calcul

```python
def get_workouts_count_last_week(user_id: str) -> int
    """Compte le nombre de séances de la semaine dernière"""

def get_exercises_count_last_week(user_id: str) -> int
    """Compte le nombre d'exercices de la semaine dernière"""
```

### Fonctions Améliorées

```python
def getsessionsbyid(user_id: str) -> dict
    """Récupère les stats avec user_id au lieu de email"""
    
def getallemail() -> list
    """Ajout de logs et gestion d'erreurs"""
    
def getclientbyid(email: str) -> dict
    """Ajout de logs détaillés"""
```

---

## 🧪 Tests à Effectuer

### 1. Test de l'Endpoint de Debug
```bash
curl -X GET https://votre-api.vercel.app/debug/test-supabase \
  -H "x-api-key: VOTRE_CLE_API"
```

Vérifier que :
- `supabase_connected: true`
- `total_users` > 0
- `test_user_workouts_last_week.seances_count` affiche le bon nombre

### 2. Test de l'Envoi d'Email
```bash
curl -X POST https://votre-api.vercel.app/send-weekly-email \
  -H "x-api-key: VOTRE_CLE_API"
```

Vérifier que :
- L'email reçu affiche **0** si aucune séance la semaine dernière
- L'email affiche le bon nombre si des séances ont été faites

---

## 📝 Variables d'Environnement Nécessaires

Pour Vercel, configurer :

```env
API_KEY=votre_cle_api_secrete
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=votre_email@gmail.com
SMTP_PASSWORD=mot_de_passe_application
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=votre_cle_service_role
```

---

## 🚀 Déploiement

### 1. Push sur GitHub
```bash
git add .
git commit -m "Fix: Correction des statistiques hebdomadaires et requêtes Supabase"
git push origin main
```

### 2. Configuration Vercel
- Le déploiement est automatique après le push
- Vérifier que les variables d'environnement sont bien configurées

### 3. Test Post-Déploiement
- Tester l'endpoint `/debug/test-supabase`
- Vérifier les logs dans le dashboard Vercel
- Envoyer un email de test

---

## 📌 Points Importants

1. **Deux fichiers à maintenir :**
   - `api/index.py` : Utilisé par Vercel (PRIORITÉ)
   - `envmail.py` : Pour le développement local

2. **Logs détaillés :**
   - Tous les logs sont visibles dans le dashboard Vercel
   - Utiliser l'endpoint de debug pour tester

3. **Période calculée :**
   - La "semaine dernière" = du lundi au dimanche de la semaine précédente
   - Calculée avec `week_bounds_previous()`

---

## ✅ Checklist de Vérification

- [x] Correction de `getsessionsbyid()` pour utiliser `user_id`
- [x] Ajout de `get_workouts_count_last_week()`
- [x] Ajout de `get_exercises_count_last_week()`
- [x] Correction des variables envoyées au template
- [x] Ajout du système de logging complet
- [x] Correction de la configuration SMTP
- [x] Création de l'endpoint de debug
- [x] Gestion d'erreurs robuste
- [x] Configuration Vercel (`vercel.json`)
- [x] Documentation complète

---

**Résultat : Les emails affichent maintenant les statistiques correctes de la semaine dernière ! 🎉**

