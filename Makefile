.PHONY: help build up down logs shell migrate createsuperuser seed test prod-build prod-up

help:
	@echo "Commandes disponibles:"
	@echo "  make dev          - Démarrer en environnement de développement"
	@echo "  make prod-build   - Construire les images pour production"
	@echo "  make prod-up      - Démarrer en production"
	@echo "  make down         - Arrêter tous les conteneurs"
	@echo "  make logs         - Voir les logs"
	@echo "  make shell-web    - Entrer dans le conteneur web"
	@echo "  make shell-db     - Entrer dans PostgreSQL"
	@echo "  make migrate      - Appliquer les migrations"
	@echo "  make createsuperuser - Créer un superutilisateur"
	@echo "  make seed         - Peupler la base de données"
	@echo "  make test         - Lancer les tests"

dev:
	docker-compose -f docker-compose.dev.yml up --build

prod-build:
	docker-compose build --no-cache

prod-up:
	docker-compose up -d
	@echo "Application disponible sur http://localhost"

down:
	docker-compose down -v

logs:
	docker-compose logs -f

logs-web:
	docker-compose logs -f web

shell-web:
	docker-compose exec web bash

shell-db:
	docker-compose exec db psql -U postgres -d ticket_platform

migrate:
	docker-compose exec web python manage.py migrate

createsuperuser:
	docker-compose exec web python manage.py createsuperuser

seed:
	docker-compose exec web python manage.py seed_db

test:
	docker-compose exec web python manage.py test

restart:
	docker-compose restart web celery

clean:
	docker-compose down -v
	docker system prune -f