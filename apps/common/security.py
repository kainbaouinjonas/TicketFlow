import re

class InputSanitizer:
    @staticmethod
    def sanitize_text(text, max_length=1000):
        if not text:
            return ''
        if len(text) > max_length:
            text = text[:max_length]
        return text
    
    @staticmethod
    def sanitize_email(email):
        if not email:
            return ''
        email = email.lower().strip()
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError("Email invalide")
        return email
    
    @staticmethod
    def sanitize_username(username):
        if not username:
            return ''
        return re.sub(r'[^a-zA-Z0-9_.-]', '', username)[:150]


class PasswordValidator:
    @staticmethod
    def validate_strength(password):
        errors = []
        if len(password) < 8:
            errors.append("8 caractères minimum")
        if not re.search(r'[A-Z]', password):
            errors.append("Une majuscule requise")
        if not re.search(r'[a-z]', password):
            errors.append("Une minuscule requise")
        if not re.search(r'[0-9]', password):
            errors.append("Un chiffre requis")
        return len(errors) == 0, errors


class RateLimiter:
    def __init__(self, key, limit, period):
        self.key = key
        self.limit = limit
        self.period = period
    
    def check(self, identifier):
        return True, 0
