from django.db import models
from django.conf import settings
from django.utils.text import slugify
from common.validators import SecurityValidators

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom de catégorie")
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    def clean(self):
        SecurityValidators.validate_no_html(self.name)


class Event(models.Model):
    title = models.CharField(max_length=200, verbose_name="Titre de l'événement")
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name="Organisateur"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='events',
        verbose_name="Catégorie"
    )
    description = models.TextField(verbose_name="Description")
    banner = models.ImageField(
        upload_to='events/banners/',
        blank=True,
        null=True,
        verbose_name="Image de bannière"
    )
    location = models.CharField(max_length=255, verbose_name="Lieu de l'événement")
    start_time = models.DateTimeField(verbose_name="Date de début")
    end_time = models.DateTimeField(verbose_name="Date de fin")
    is_published = models.BooleanField(default=True, verbose_name="Publié")
    total_capacity = models.PositiveIntegerField(verbose_name="Capacité totale")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix de l'événement", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ['-start_time']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    def clean(self):
        SecurityValidators.validate_no_html(self.title)
        SecurityValidators.validate_no_sql(self.location)
        SecurityValidators.validate_capacity(self.total_capacity)
        if self.start_time and self.end_time:
            SecurityValidators.validate_event_dates(self.start_time, self.end_time)


class Seat(models.Model):
    SEAT_VIP = 'VIP'
    SEAT_GOLD = 'GOLD'
    SEAT_STANDARD = 'STANDARD'

    SEAT_CATEGORIES = [
        (SEAT_VIP, 'Premium VIP'),
        (SEAT_GOLD, 'Zone Or'),
        (SEAT_STANDARD, 'Standard'),
    ]

    STATUS_AVAILABLE = 'AVAILABLE'
    STATUS_LOCKED = 'LOCKED'
    STATUS_RESERVED = 'RESERVED'

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, 'Disponible'),
        (STATUS_LOCKED, 'Verrouillé temporairement'),
        (STATUS_RESERVED, 'Réservé / Payé'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='seats',
        verbose_name="Événement"
    )
    row = models.CharField(max_length=10, verbose_name="Rangée")
    number = models.PositiveIntegerField(verbose_name="Numéro de siège")
    category = models.CharField(
        max_length=20,
        choices=SEAT_CATEGORIES,
        default=SEAT_STANDARD,
        verbose_name="Catégorie de place"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Prix"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_AVAILABLE,
        verbose_name="Statut"
    )
    locked_by_session = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ID de session verrouillante"
    )
    locked_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date de verrouillage"
    )
    version = models.PositiveIntegerField(
        default=1,
        verbose_name="Version"
    )

    class Meta:
        verbose_name = "Siège"
        verbose_name_plural = "Sièges"
        unique_together = ('event', 'row', 'number')
        ordering = ['row', 'number']

    def __str__(self):
        return f"{self.event.title} - Siège {self.row}{self.number}"
    
    def clean(self):
        SecurityValidators.validate_price(self.price)