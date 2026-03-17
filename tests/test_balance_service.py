import pytest
from app.services import balance_service, transaction_service
from app.models.balance import Balance
from tests.conftest import verify_balance_integrity


def test_credit_and_get(app, db, regular_user, second_user):
    with app.app_context():
        balance_service.credit_balance(regular_user.id, second_user.id, 1.5)
        db.session.commit()
        assert abs(balance_service.get_source_balance(regular_user.id, second_user.id) - 1.5) < 1e-9
        assert abs(balance_service.get_total_balance(regular_user.id) - 1.5) < 1e-9


def test_debit_fifo(app, db, regular_user, second_user, third_user):
    with app.app_context():
        # Credit from two sources
        balance_service.credit_balance(regular_user.id, second_user.id, 1.0)  # source=bob
        balance_service.credit_balance(regular_user.id, third_user.id, 2.0)   # source=charlie
        db.session.flush()

        # Debit 1.5 - should take all 1.0 from bob (lower ID), 0.5 from charlie
        result = balance_service.debit_fifo(regular_user.id, 1.5)
        db.session.commit()

        assert result is True
        assert abs(balance_service.get_source_balance(regular_user.id, second_user.id)) < 1e-9
        assert abs(balance_service.get_source_balance(regular_user.id, third_user.id) - 1.5) < 1e-9


def test_rebuild_all_balances(app, db, regular_user, second_user, third_user):
    with app.app_context():
        # Create a bounty payout and a send
        transaction_service.record_bounty_payout(regular_user.id, second_user.id, 3.0, 'test')
        transaction_service.record_send(second_user.id, third_user.id, 1.0)
        db.session.commit()

        # Verify current state
        verify_balance_integrity(app)

        # Rebuild and verify again
        balance_service.rebuild_all_balances()
        db.session.commit()

        verify_balance_integrity(app)

        # Bob should have 2.0 from Alice, Charlie 1.0 from Bob
        assert abs(balance_service.get_source_balance(second_user.id, regular_user.id) - 2.0) < 1e-9
        assert abs(balance_service.get_source_balance(third_user.id, second_user.id) - 1.0) < 1e-9
