import uuid
import random
import time

class BasePaymentGateway:
    def process_charge(self, amount, currency, reservation_id, **kwargs):
        raise NotImplementedError

class StripeMockGateway(BasePaymentGateway):
    def process_charge(self, amount, currency, reservation_id, **kwargs):
        time.sleep(0.5)
        tx_id = f"ch_stripe_{uuid.uuid4().hex[:16]}"
        return {
            'success': True,
            'transaction_id': tx_id,
            'status': 'SUCCESS',
            'logs': f"Stripe charged {amount} {currency}"
        }

class PayPalMockGateway(BasePaymentGateway):
    def process_charge(self, amount, currency, reservation_id, **kwargs):
        time.sleep(0.5)
        tx_id = f"pay_paypal_{uuid.uuid4().hex[:16]}"
        return {
            'success': True,
            'transaction_id': tx_id,
            'status': 'SUCCESS',
            'logs': f"PayPal success for {amount} {currency}"
        }

class MobileMoneyMockGateway(BasePaymentGateway):
    def initiate_transaction(self, phone_number, amount, currency, provider):
        otp = str(random.randint(100000, 999999))
        tx_id = f"tx_{provider.lower()}_{uuid.uuid4().hex[:16]}"
        return {
            'success': True,
            'transaction_id': tx_id,
            'otp': otp,
            'status': 'PENDING',
            'logs': f"Initiated {provider} transaction"
        }
        
    def verify_otp(self, transaction_id, user_otp, correct_otp):
        if user_otp == correct_otp:
            return {'success': True, 'status': 'SUCCESS', 'logs': "OTP verified"}
        else:
            return {'success': False, 'status': 'FAILED', 'logs': "Invalid OTP"}