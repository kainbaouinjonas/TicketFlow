"""
Validateurs de sécurité avancés pour tous les modèles
Protection : Injection, XSS, validation de données
"""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SecurityValidators:
    """Collection de validateurs de sécurité"""
    
    @staticmethod
    def validate_no_html(value):
        """Interdit tout contenu HTML"""
        html_patterns = [
            r'<[^>]*>',           # Balises HTML
            r'&[a-z]+;',          # Entités HTML
            r'&#[0-9]+;',         # Entités numériques
            r'javascript:',       # Protocole JS
            r'data:text/html',    # Data URI HTML
        ]
        
        for pattern in html_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError("Le HTML n'est pas autorisé dans ce champ.")
        
        return value
    
    @staticmethod
    def validate_no_sql(value):
        """Interdit les patterns SQL"""
        sql_patterns = [
            r'(?i)\bSELECT\b.*\bFROM\b',
            r'(?i)\bINSERT\b.*\bINTO\b',
            r'(?i)\bUPDATE\b.*\bSET\b',
            r'(?i)\bDELETE\b.*\bFROM\b',
            r'(?i)\bDROP\b.*\bTABLE\b',
            r'(?i)\bUNION\b.*\bSELECT\b',
            r'--',
            r';.*DROP',
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError("Contenu suspect détecté.")
        
        return value
    
    @staticmethod
    def validate_event_dates(start_time, end_time):
        """Valide les dates d'événement"""
        now = timezone.now()
        
        if start_time <= now:
            raise ValidationError("La date de début doit être dans le futur.")
        
        if end_time <= start_time:
            raise ValidationError("La date de fin doit être postérieure à la date de début.")
        
        if end_time > start_time + timedelta(days=30):
            raise ValidationError("Un événement ne peut pas durer plus de 30 jours.")
        
        return start_time, end_time
    
    @staticmethod
    def validate_price(price):
        """Valide un prix"""
        if not isinstance(price, (int, float, Decimal)):
            raise ValidationError("Format de prix invalide.")
        
        if price < 0:
            raise ValidationError("Le prix ne peut pas être négatif.")
        
        if price > 10000:
            raise ValidationError("Le prix maximum est de 10 000 €.")
        
        # 2 décimales max
        if isinstance(price, Decimal) and price.as_tuple().exponent < -2:
            raise ValidationError("Le prix ne peut pas avoir plus de 2 décimales.")
        
        return price
    
    @staticmethod
    def validate_capacity(capacity):
        """Valide une capacité"""
        if not isinstance(capacity, int):
            raise ValidationError("La capacité doit être un nombre entier.")
        
        if capacity < 1:
            raise ValidationError("La capacité doit être au moins 1.")
        
        if capacity > 100000:
            raise ValidationError("La capacité maximale est de 100 000 places.")
        
        return capacity
    
    @staticmethod
    def validate_seat_number(row, number, total_rows=10, seats_per_row=10):
        """Valide un numéro de siège"""
        if not isinstance(number, int):
            raise ValidationError("Le numéro de siège doit être un nombre entier.")
        
        if number < 1 or number > seats_per_row:
            raise ValidationError(f"Le numéro de siège doit être entre 1 et {seats_per_row}.")
        
        if row not in [chr(65 + i) for i in range(total_rows)]:
            raise ValidationError(f"La rangée doit être entre A et {chr(65 + total_rows - 1)}.")
        
        return row, number


class CreditCardValidator:
    """Validation des numéros de carte bancaire (algorithme de Luhn)"""
    
    @staticmethod
    def luhn_check(card_number):
        """Vérification Luhn"""
        card_number = re.sub(r'\D', '', card_number)
        
        if not card_number.isdigit():
            return False
        
        total = 0
        is_second = False
        
        for digit in reversed(card_number):
            d = int(digit)
            if is_second:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
            is_second = not is_second
        
        return total % 10 == 0
    
    @staticmethod
    def get_card_type(card_number):
        """Détecte le type de carte"""
        card_number = re.sub(r'\D', '', card_number)
        
        patterns = {
            'VISA': r'^4[0-9]{12}(?:[0-9]{3})?$',
            'MASTERCARD': r'^(5[1-5][0-9]{14}|2(22[1-9][0-9]{12}|2[3-9][0-9]{13}|[3-6][0-9]{14}|7[0-1][0-9]{13}|720[0-9]{12}))$',
            'AMEX': r'^3[47][0-9]{13}$',
            'DISCOVER': r'^6(?:011|5[0-9]{2})[0-9]{12}$',
        }
        
        for card_type, pattern in patterns.items():
            if re.match(pattern, card_number):
                return card_type
        
        return 'UNKNOWN'
    
    def validate(self, card_number, expiry_month, expiry_year, cvv):
        """Validation complète de carte bancaire"""
        errors = []
        
        # Nettoyer le numéro
        card_number = re.sub(r'\D', '', card_number)
        
        # Vérifier la longueur
        if len(card_number) not in [15, 16]:
            errors.append("Numéro de carte invalide.")
        
        # Vérification Luhn
        if not self.luhn_check(card_number):
            errors.append("Numéro de carte invalide.")
        
        # Vérifier la date d'expiration
        try:
            now = datetime.now()
            expiry = datetime(int(expiry_year), int(expiry_month), 1)
            if expiry < now:
                errors.append("Carte expirée.")
            if expiry > now + timedelta(days=365 * 10):
                errors.append("Date d'expiration trop lointaine.")
        except (ValueError, TypeError):
            errors.append("Date d'expiration invalide.")
        
        # Vérifier CVV
        if not cvv.isdigit() or len(cvv) not in [3, 4]:
            errors.append("CVV invalide.")
        
        return len(errors) == 0, errors


class IBANValidator:
    """Validation des IBAN européens"""
    
    @staticmethod
    def validate(iban):
        """Valide un IBAN"""
        iban = iban.upper().replace(' ', '')
        
        # Vérifier la longueur par pays
        country_lengths = {
            'FR': 27, 'DE': 22, 'IT': 27, 'ES': 24, 'BE': 16,
            'NL': 18, 'CH': 21, 'AT': 20, 'LU': 20, 'PT': 25
        }
        
        country = iban[:2]
        if country not in country_lengths:
            return False
        
        if len(iban) != country_lengths[country]:
            return False
        
        # Vérification modulo 97
        iban_moved = iban[4:] + iban[:4]
        iban_numbers = ''
        
        for char in iban_moved:
            if char.isdigit():
                iban_numbers += char
            else:
                iban_numbers += str(ord(char) - 55)
        
        return int(iban_numbers) % 97 == 1