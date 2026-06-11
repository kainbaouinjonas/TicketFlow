from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@ticketflow.com",
        "password": "Admin@123456",
        "role": "ADMIN",
        "is_staff": True,
        "is_superuser": True,
        "label": "Super-Admin",
    },
    {
        "username": "controller",
        "email": "controller@ticketflow.com",
        "password": "Controller@123456",
        "role": "CONTROLLER",
        "is_staff": False,
        "is_superuser": False,
        "label": "Contrôleur",
    },
    {
        "username": "organizer",
        "email": "organizer@ticketflow.com",
        "password": "Organizer@123456",
        "role": "ORGANIZER",
        "is_staff": False,
        "is_superuser": False,
        "label": "Organisateur",
    },
]


class Command(BaseCommand):
    help = "Crée les trois utilisateurs de démonstration (admin, controller, organizer)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== Création des utilisateurs de démonstration TicketFlow ===\n"
        ))

        created_count = 0
        skipped_count = 0

        for data in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": data["email"],
                    "role": data["role"],
                    "is_staff": data["is_staff"],
                    "is_superuser": data["is_superuser"],
                },
            )

            # Always refresh the password so the demo credentials stay valid
            # even if the user already existed with a different password.
            user.set_password(data["password"])

            # Ensure role and privilege flags are up-to-date on existing users.
            user.email = data["email"]
            user.role = data["role"]
            user.is_staff = data["is_staff"]
            user.is_superuser = data["is_superuser"]
            user.save()

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"  [CRÉÉ]   {data['label']:15s} → {data['username']}")
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f"  [EXISTANT] {data['label']:15s} → {data['username']} (mis à jour)")
                )
                skipped_count += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Terminé : {created_count} créé(s), {skipped_count} mis à jour."
        ))
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== Identifiants de connexion ==="))
        self.stdout.write("")
        self.stdout.write(f"  {'Rôle':<15} {'Nom d\\'utilisateur':<15} {'Mot de passe':<20} {'Email'}")
        self.stdout.write(f"  {'-'*15} {'-'*15} {'-'*20} {'-'*30}")
        for data in DEMO_USERS:
            self.stdout.write(
                f"  {data['label']:<15} {data['username']:<15} {data['password']:<20} {data['email']}"
            )
        self.stdout.write("")
