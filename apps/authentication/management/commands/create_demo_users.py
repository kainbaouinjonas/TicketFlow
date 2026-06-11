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
        "label": "Administrateur",
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
    help = "Crée trois utilisateurs de démonstration : ADMIN, CONTROLLER et ORGANIZER"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== Création des utilisateurs de démonstration TicketFlow ===\n"
        ))

        created_count = 0
        skipped_count = 0

        for user_data in DEMO_USERS:
            username = user_data["username"]
            existing = User.objects.filter(username=username).first()

            if existing:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [IGNORÉ]  L'utilisateur '{username}' existe déjà."
                    )
                )
                skipped_count += 1
                continue

            user = User(
                username=username,
                email=user_data["email"],
                role=user_data["role"],
                is_staff=user_data["is_staff"],
                is_superuser=user_data["is_superuser"],
            )
            user.set_password(user_data["password"])
            user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"  [CRÉÉ]    {user_data['label']} '{username}' créé avec succès."
                )
            )
            created_count += 1

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== Récapitulatif des comptes de démonstration ===\n"))
        self.stdout.write(f"  {'Rôle':<14} {'Nom d\\'utilisateur':<14} {'Email':<32} Mot de passe")
        self.stdout.write(f"  {'-'*14} {'-'*14} {'-'*32} {'-'*20}")

        for user_data in DEMO_USERS:
            self.stdout.write(
                f"  {user_data['label']:<14} "
                f"{user_data['username']:<14} "
                f"{user_data['email']:<32} "
                f"{user_data['password']}"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Terminé : {created_count} créé(s), {skipped_count} ignoré(s).")
        )
