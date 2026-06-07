import logging
import re

class SensitiveDataFilter(logging.Filter):
    """
    Filtre pour masquer les données sensibles dans les logs
    """
    
    SENSITIVE_PATTERNS = [
        (r'password[=:]\s*\S+', 'password=[HIDDEN]'),
        (r'token[=:]\s*\S+', 'token=[HIDDEN]'),
        (r'api_key[=:]\s*\S+', 'api_key=[HIDDEN]'),
        (r'secret[=:]\s*\S+', 'secret=[HIDDEN]'),
        (r'authorization[=:]\s*\S+', 'authorization=[HIDDEN]'),
        (r'bearer\s+\S+', 'bearer [HIDDEN]', re.IGNORECASE),
        (r'card_number[=:]\s*\d+', 'card_number=[HIDDEN]'),
        (r'cvv[=:]\s*\d+', 'cvv=[HIDDEN]'),
        (r'otp[=:]\s*\d+', 'otp=[HIDDEN]'),
    ]
    
    def filter(self, record):
        msg = record.getMessage()
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            if isinstance(pattern, tuple):
                msg = re.sub(pattern[0], pattern[1], msg, flags=pattern[2] if len(pattern) > 2 else 0)
            else:
                msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        record.msg = msg
        return True