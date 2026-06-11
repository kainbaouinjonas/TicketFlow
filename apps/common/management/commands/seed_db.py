from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from events.models import Category, Event, Seat
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = "Semer la base de données de test avec des données enterprise"

    def handle(self, *args, **options):
        self.stdout.write("Début du peuplement de la base de données...")
        
        with transaction.atomic():
            # Create Users
            self.stdout.write("Création des comptes d'utilisateurs...")
            
            admin, _ = User.objects.get_or_create(
                username="admin",
                defaults={
                    "email": "admin@ticket.fr",
                    "role": User.ROLE_ADMIN,
                    "is_staff": True,
                    "is_superuser": True
                }
            )
            admin.set_password("Admin1234!")
            admin.save()
            
            controller, _ = User.objects.get_or_create(
                username="controller",
                defaults={
                    "email": "controller@ticket.fr",
                    "role": User.ROLE_CONTROLLER,
                }
            )
            controller.set_password("controllerpass")
            controller.save()

            organizer, _ = User.objects.get_or_create(
                username="organizer",
                defaults={
                    "email": "organizer@ticket.fr",
                    "role": User.ROLE_ORGANIZER,
                }
            )
            organizer.set_password("organizerpass")
            organizer.save()

            customer, _ = User.objects.get_or_create(
                username="user",
                defaults={
                    "email": "user@ticket.fr",
                    "role": User.ROLE_USER,
                }
            )
            customer.set_password("userpass")
            customer.save()

            # Create Categories
            self.stdout.write("Création des catégories...")
            cat_concert, _ = Category.objects.get_or_create(name="Concerts", defaults={"slug": "concerts"})
            cat_sport, _ = Category.objects.get_or_create(name="Matchs de Sport", defaults={"slug": "matchs-de-sport"})
            cat_conference, _ = Category.objects.get_or_create(name="Conférence", defaults={"slug": "conference"})
            cat_mariage, _ = Category.objects.get_or_create(name="Mariage & Cérémonie", defaults={"slug": "mariage-ceremonie"})
            
            # Suppression des anciens événements
            self.stdout.write("Suppression des anciens événements...")
            Event.objects.all().delete()

            events_data = [
                {
                    "title": "Grand Concert de Musique de Bamenda",
                    "category": cat_concert,
                    "location": "Palais des Congrès de Bamenda, Cameroun",
                    "description": "Une magnifique soirée de célébration musicale live avec des artistes camerounais.",
                    "offset_days": 10
                },
                {
                    "title": "Tournoi de Football Inter-Quartiers",
                    "category": cat_sport,
                    "location": "Stade Municipal de Bamenda, Cameroun",
                    "description": "Le tournoi de football local le plus attendu de l'année opposant les meilleures équipes.",
                    "offset_days": 15
                },
                {
                    "title": "Forum d'Innovation Tech Bamenda",
                    "category": cat_conference,
                    "location": "Bamenda Congress Hall, Cameroun",
                    "description": "Découvrez les dernières innovations technologiques, opportunités d'entrepreneuriat et IA.",
                    "offset_days": 8
                },
                {
                    "title": "Festival Culturel de Bamenda",
                    "category": cat_mariage,
                    "location": "Bamenda Cultural Plaza, Cameroun",
                    "description": "Célébration des danses et des traditions culturelles locales de la région du Nord-Ouest.",
                    "offset_days": 20
                }
            ]

            for ev in events_data:
                event, created = Event.objects.get_or_create(
                    title=ev["title"],
                    defaults={
                        "organizer": organizer,
                        "category": ev["category"],
                        "description": ev["description"],
                        "location": ev["location"],
                        "start_time": timezone.now() + timedelta(days=ev["offset_days"]),
                        "end_time": timezone.now() + timedelta(days=ev["offset_days"], hours=3),
                        "total_capacity": 50,
                        "is_published": True
                    }
                )
                
                if created or not Seat.objects.filter(event=event).exists():
                    rows = ['A', 'B', 'C', 'D', 'E']
                    for r in rows:
                        for n in range(1, 11):
                            seat_category = Seat.SEAT_STANDARD
                            price = 25.00
                            
                            if r == 'A':
                                seat_category = Seat.SEAT_VIP
                                price = 120.00
                            elif r in ['B', 'C']:
                                seat_category = Seat.SEAT_GOLD
                                price = 60.00
                                
                            Seat.objects.create(
                                event=event,
                                row=r,
                                number=n,
                                category=seat_category,
                                price=price,
                                status=Seat.STATUS_AVAILABLE
                            )
                            
        self.stdout.write(self.style.SUCCESS("Base de données semée avec succès !"))
        self.stdout.write(self.style.WARNING("Comptes créés :"))
        self.stdout.write("  - Admin: admin / adminpass")
        self.stdout.write("  - Controller: controller / controllerpass")
        self.stdout.write("  - Organizer: organizer / organizerpass")
        self.stdout.write("  - Customer: user / userpass")