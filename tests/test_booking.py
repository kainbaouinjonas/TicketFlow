import pytest
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import transaction, DatabaseError
from events.models import Category, Event, Seat
from reservations.models import Cart, CartItem, Reservation
from reservations.tasks import release_expired_carts_and_reservations
from payments.models import Payment
from tickets.models import Ticket
import threading
import time

User = get_user_model()

@pytest.fixture
def setup_db(db):
    """
    Establish fundamental categories, users and events in database.
    """
    admin, _ = User.objects.get_or_create(
        username="admin_test_booking",
        defaults={"email": "admin_booking@test.fr", "is_staff": True, "is_superuser": True}
    )
    if not admin.has_usable_password():
        admin.set_password("pass")
        admin.save()
    customer1, _ = User.objects.get_or_create(
        username="cust1_booking",
        defaults={"email": "cust1_booking@test.fr"}
    )
    if not customer1.has_usable_password():
        customer1.set_password("pass")
        customer1.save()
    customer2, _ = User.objects.get_or_create(
        username="cust2_booking",
        defaults={"email": "cust2_booking@test.fr"}
    )
    if not customer2.has_usable_password():
        customer2.set_password("pass")
        customer2.save()
    
    category, _ = Category.objects.get_or_create(name="Matchs de Sport")
    event = Event.objects.create(
        title="Match de Tennis",
        organizer=admin,
        category=category,
        description="Match test",
        location="Stade Test",
        start_time=timezone.now() + timedelta(days=1),
        end_time=timezone.now() + timedelta(days=1, hours=2),
        total_capacity=10
    )
    
    seat1 = Seat.objects.create(
        event=event, row="A", number=1, category=Seat.SEAT_VIP, price=100.00
    )
    seat2 = Seat.objects.create(
        event=event, row="A", number=2, category=Seat.SEAT_STANDARD, price=20.00
    )
    
    return {
        "event": event,
        "seat1": seat1,
        "seat2": seat2,
        "cust1": customer1,
        "cust2": customer2,
    }


@pytest.mark.django_db(transaction=True)
def test_seat_concurrency_race_condition(setup_db):
    """
    Simulate parallel threads trying to book the exact same seat simultaneously.
    Asserts that at most one thread succeeds and the second thread is blocked.
    """
    from django.db import connection
    if connection.vendor == 'sqlite':
        pytest.skip("SQLite doesn't support concurrent writes in multi-threaded test environment")
        
    seat = setup_db["seat1"]
    
    success_results = []
    errors = []
    
    def book_seat_thread(user_session_id):
        from django.db import connections
        try:
            # Each thread needs its own connection
            with transaction.atomic():
                selected_seat = Seat.objects.select_for_update().get(id=seat.id)
                if selected_seat.status == Seat.STATUS_AVAILABLE:
                    # Small delay to increase chance of race triggers
                    time.sleep(0.1)
                    selected_seat.status = Seat.STATUS_LOCKED
                    selected_seat.locked_by_session = user_session_id
                    selected_seat.locked_at = timezone.now()
                    selected_seat.save()
                    success_results.append(user_session_id)
                else:
                    errors.append("Already locked")
        except Exception as e:
            errors.append(str(e))
        finally:
            connections.close_all()

    # Thread 1 and 2 start simultaneously
    t1 = threading.Thread(target=book_seat_thread, args=("session_alpha",))
    t2 = threading.Thread(target=book_seat_thread, args=("session_beta",))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    # Assertions
    assert len(success_results) == 1, f"Only one user should successfully lock the seat. Success: {success_results}, Errors: {errors}"
    assert Seat.objects.get(id=seat.id).status == Seat.STATUS_LOCKED


def test_cart_expiration_cleanup_task(setup_db, db):
    """
    Create an expired cart with a locked seat. Run background task and assert
    that the seat is freed and cart is deleted successfully.
    """
    seat = setup_db["seat2"]
    
    # Lock seat in expired cart
    cart = Cart.objects.create(
        session_id="expired_session",
        expires_at=timezone.now() - timedelta(minutes=5)
    )
    CartItem.objects.create(cart=cart, seat=seat)
    
    seat.status = Seat.STATUS_LOCKED
    seat.locked_by_session = "expired_session"
    seat.locked_at = timezone.now() - timedelta(minutes=5)
    seat.save()
    
    # Run the background task
    res = release_expired_carts_and_reservations()
    
    # Assert seat is available again
    seat.refresh_from_db()
    assert seat.status == Seat.STATUS_AVAILABLE
    assert seat.locked_by_session is None
    
    # Assert cart is deleted
    assert not Cart.objects.filter(session_id="expired_session").exists()


def test_payment_and_hmac_ticket_generation(setup_db, db):
    """
    Test creating a pending reservation, simulating OTP verification success,
    confirming the payment and generating cryptographic signed tickets.
    """
    cust = setup_db["cust1"]
    seat = setup_db["seat2"]
    
    # Create reservation
    res = Reservation.objects.create(
        user=cust,
        total_price=20.00,
        status=Reservation.STATUS_PENDING,
        expires_at=timezone.now() + timedelta(minutes=15)
    )
    res.seats.add(seat)
    
    # Update seat status
    seat.status = Seat.STATUS_LOCKED
    seat.save()
    
    # Create Payment
    payment = Payment.objects.create(
        reservation=res,
        amount=20.00,
        method=Payment.METHOD_ORANGE,
        status=Payment.STATUS_PENDING,
        transaction_id="tx_om_12345",
        phone_number="0707070707",
        otp_code="999999"
    )
    
    # Verify OTP successfully
    payment.status = Payment.STATUS_SUCCESS
    payment.save()
    
    # Verify Reservation Success Action
    with transaction.atomic():
        res.status = Reservation.STATUS_CONFIRMED
        res.save()
        
        seat.status = Seat.STATUS_RESERVED
        seat.save()
        
        # Call tickets generator
        from payments.views import generate_tickets_for_reservation
        generate_tickets_for_reservation(res)
        
    # Assertions
    res.refresh_from_db()
    seat.refresh_from_db()
    assert res.status == Reservation.STATUS_CONFIRMED
    assert seat.status == Seat.STATUS_RESERVED
    
    # Assert Ticket generated with cryptographed hash
    ticket = Ticket.objects.get(reservation=res, seat=seat)
    assert ticket.is_validated is False
    assert ticket.qr_code_hash is not None
    assert len(ticket.qr_code_hash) > 10


def test_celery_generate_tickets_task(setup_db, db):
    """
    Test generate_tickets_async Celery task directly.
    """
    cust = setup_db["cust1"]
    seat = setup_db["seat2"]
    res = Reservation.objects.create(
        user=cust,
        total_price=20.00,
        status=Reservation.STATUS_CONFIRMED,
        expires_at=timezone.now() + timedelta(minutes=15)
    )
    res.seats.add(seat)
    
    # Run task directly (mocking Celery worker execution)
    from tickets.tasks import generate_tickets_async
    result = generate_tickets_async(res.id)
    assert "billets créés" in result or "billets" in result
    
    # Check ticket is created
    assert Ticket.objects.filter(reservation=res, seat=seat).exists()


def test_celery_send_payment_confirmation_email_task(setup_db, db):
    """
    Test send_payment_confirmation_email Celery task directly.
    """
    from django.core import mail
    from payments.tasks import send_payment_confirmation_email
    cust = setup_db["cust1"]
    res = Reservation.objects.create(
        user=cust,
        total_price=20.00,
        status=Reservation.STATUS_CONFIRMED,
        expires_at=timezone.now() + timedelta(minutes=15)
    )
    payment = Payment.objects.create(
        reservation=res,
        amount=20.00,
        method=Payment.METHOD_CARD,
        status=Payment.STATUS_SUCCESS,
        transaction_id="tx_test_email_123"
    )
    
    # Ensure mail outbox is empty
    mail.outbox = []
    
    result = send_payment_confirmation_email(payment.id)
    assert "Email envoyé" in result
    
    # Assert mail is sent
    assert len(mail.outbox) == 1
    assert "Confirmation de paiement" in mail.outbox[0].subject
    assert cust.email in mail.outbox[0].to


def test_celery_cleanup_failed_payments_task(setup_db, db):
    """
    Test cleanup_failed_payments task.
    """
    from django.utils import timezone
    from datetime import timedelta
    from payments.tasks import cleanup_failed_payments
    cust = setup_db["cust1"]
    res = Reservation.objects.create(
        user=cust,
        total_price=20.00,
        status=Reservation.STATUS_PENDING,
        expires_at=timezone.now() + timedelta(minutes=15)
    )
    # Create a stale payment
    payment = Payment.objects.create(
        reservation=res,
        amount=20.00,
        method=Payment.METHOD_CARD,
        status=Payment.STATUS_PENDING,
        transaction_id="tx_stale_123"
    )
    # Manually update created_at to be older than 1 hour (since auto_now_add makes it read-only on save, we do .update())
    Payment.objects.filter(id=payment.id).update(created_at=timezone.now() - timedelta(hours=2))
    
    # Run cleanup
    result = cleanup_failed_payments()
    assert "nettoyés" in result
    
    payment.refresh_from_db()
    assert payment.status == Payment.STATUS_FAILED


def test_celery_cleanup_orphaned_tickets_task(setup_db, db):
    """
    Test cleanup_orphaned_tickets task.
    """
    from tickets.tasks import cleanup_orphaned_tickets
    cust = setup_db["cust1"]
    seat = setup_db["seat2"]
    res = Reservation.objects.create(
        user=cust,
        total_price=20.00,
        status=Reservation.STATUS_CANCELLED,
        expires_at=timezone.now() - timedelta(minutes=15)
    )
    ticket = Ticket.objects.create(
        reservation=res,
        seat=seat,
        qr_code_hash="fake_signature_hash"
    )
    
    # Run cleanup
    result = cleanup_orphaned_tickets()
    assert "orphelins" in result
    
    assert not Ticket.objects.filter(id=ticket.id).exists()

