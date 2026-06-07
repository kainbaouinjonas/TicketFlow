from django.contrib import admin
from django.utils.html import format_html
from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_code', 'reservation', 'seat_display', 'is_validated', 'qr_link']
    list_filter = ['is_validated', 'seat__event']
    search_fields = ['ticket_code', 'qr_code_hash']
    readonly_fields = ['ticket_code', 'qr_code_hash', 'created_at']
    
    def seat_display(self, obj):
        return f"{obj.seat.row}{obj.seat.number} - {obj.seat.event.title}"
    seat_display.short_description = "Siège"
    
    def qr_link(self, obj):
        if obj.ticket_code:
            return format_html('<a href="{}" target="_blank">QR</a>', f'/tickets/qr/{obj.ticket_code}/')
        return "-"
    qr_link.short_description = "QR"