# TicketFlow - Plateforme de Billetterie Enterprise

Une plateforme de billetterie événementielle hautement scalable avec réservation en temps réel, WebSockets, et paiements simulés.

## 🚀 Fonctionnalités principales

- **Verrouillage haute concurrence** des sièges avec Redis et verrous optimistes
- **WebSockets temps réel** pour mises à jour instantanées du plan de salle
- **Paiements simulés** (Stripe, PayPal, Orange Money, MTN Mobile Money)
- **QR Codes cryptographiques** signés HMAC-SHA256
- **Dashboard admin** type Stripe avec graphiques SVG dynamiques
- **Déploiement cloud** avec Kubernetes et Terraform

## 🛠️ Stack technique

- Backend: Django 4.2, Channels, Celery
- Base de données: PostgreSQL, Redis
- Frontend: HTMX, Alpine.js, TailwindCSS
- Infrastructure: Docker, Kubernetes, Terraform (AWS)

## 💻 Installation locale

```bash
# Cloner le projet
git clone <repo>
cd projet_cursor

# Créer l'environnement virtuel
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Installer les dépendances
pip install -r requirements.txt

# Configurer la base de données
python manage.py migrate
python manage.py seed_db

# Démarrer Redis
redis-server

# Démarrer le serveur (3 terminaux)
python manage.py runserver
celery -A config worker --beat -l info