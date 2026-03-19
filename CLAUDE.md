# Thai House Coin (THC) Exchange

Fictional cryptocurrency tracker for a ~15 person work group, pegged to Thai restaurant lunch value. Invite-only, admin-managed accounts.

## Tech Stack

- **Backend:** Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate
- **Database:** SQLite (dev/test), PostgreSQL (prod on Render)
- **Frontend:** Jinja2 templates, vanilla CSS/JS
- **Tests:** pytest + pytest-flask

## Quick Reference

```bash
# Activate virtualenv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run dev server
python wsgi.py

# Seed admin user (admin/changeme)
python seed.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_wallet.py -v
```

## Project Structure

```
app/
├── __init__.py          # App factory (create_app), before_request hooks
├── extensions.py        # db, login_manager, csrf instances
├── models/              # SQLAlchemy models (User, Transaction, Balance, Bounty, Redemption)
├── routes/              # Flask blueprints (auth, admin, bounty, wallet, dashboard, etc.)
├── services/            # Business logic (balance_service, transaction_service, etc.)
├── forms/               # WTF forms
├── templates/           # Jinja2 templates
└── static/              # CSS, JS, images
tests/
├── conftest.py          # Fixtures, login() helper, mint_thc() helper, verify_balance_integrity()
└── test_*.py            # Test modules
config.py                # Config classes (Dev/Test/Prod)
wsgi.py                  # Entry point
seed.py                  # Creates admin user
```

## Key Architecture Concepts

### Source-Tagged Balances
Balances use a composite primary key `(holder_user_id, source_user_id)`. Each balance row tracks how much THC a holder has from a specific source (the bounty poster who originally minted it). This enables provenance tracking.

### FIFO Deduction
When sending THC, the sender's balances are debited in FIFO order (ascending `source_user_id`). See `debit_fifo()` in `app/services/balance_service.py`.

### Balance as Cache
The `balances` table is a materialized cache derived from transactions. It can be fully rebuilt from the transaction log via `rebuild_all_balances()`. The test helper `verify_balance_integrity()` replays all transactions and asserts they match the cached balances.

### Transaction Types
- `bounty_payout` — mints THC when a bounty claim is approved
- `send` — peer-to-peer transfer
- `burn` — destroys THC (admin action via invalidation)

### Bounty Lifecycle
OPEN → claimed by user → APPROVED (mints THC to claimant) or REJECTED

### Auth
- `admin_required` decorator in `app/routes/admin.py`
- `must_change_password` enforced via `@app.before_request` in app factory
- New users must change password on first login

## Testing Conventions

- Test config uses in-memory SQLite with CSRF disabled
- `login(client, username, password)` helper calls `/logout` first to avoid session conflicts
- `mint_thc(client, poster, claimant, amount)` creates the full bounty→claim→approve flow
- Always call `verify_balance_integrity(app)` after tests that modify balances

## Config

Three environments selected via `FLASK_ENV`:
- `development` (default) — SQLite, debug on
- `testing` — in-memory SQLite, CSRF off
- `production` — PostgreSQL via `DATABASE_URL`, auto-corrects `postgres://` to `postgresql://`
