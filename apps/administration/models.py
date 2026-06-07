from django.db import models
from django.conf import settings
from common.validators import SecurityValidators

class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="Utilisateur"
    )
    action = models.CharField(max_length=255, verbose_name="Action effectuée")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="Adresse IP")
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True, verbose_name="Détails supplémentaires")

    class Meta:
        verbose_name = "Log d'audit"
        verbose_name_plural = "Logs d'audit"
        ordering = ['-timestamp']

    def __str__(self):
        username = self.user.username if self.user else "Visiteur anonyme"
        return f"{username} - {self.action} à {self.timestamp}"
    
    def clean(self):
        self.action = SecurityValidators.validate_no_sql(self.action)
        if self.details:
            self.details = SecurityValidators.validate_no_sql(self.details)