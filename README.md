# AutoStash — Automated Debt Payoff Optimization Engine

Mimics the core Bright Money loop: sweep safe leftover cash out of checking,
then push it toward the most expensive debt first (avalanche method) —
all computed with Pandas.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

## Domain model

- **Profile** — one per user: `monthly_income`, optional `safety_buffer` override.
- **Bill** — recurring monthly bill: `amount`, `due_day`.
- **CreditCard** — `balance`, `apr`, `min_payment`.
- **SweepEvent** — a logged daily "money pull": how much was swept, where
  it went, and the full safety-math breakdown (for auditability).

## The engine (`engine/services.py`)

**`calculate_safe_to_sweep(profile, checking_balance, as_of_date)`**
Cash-flow safety math:

```
safe_to_sweep = checking_balance
                - safety_buffer
                - bills_due_in_next_5_days
capped at 25% of checking_balance, floored at 0
```

**`allocate_avalanche(cards, extra_payment)`**
Sorts cards by APR descending and dumps the swept cash into the highest-APR
card, overflowing into the next card if it covers that balance completely.

**`full_avalanche_projection(cards, monthly_extra_payment)`**
Simulates the entire payoff month-by-month (interest accrual + minimum
payments + avalanche extra payment) to report total months to debt-free
and total interest paid.

## API

All endpoints are under `/api/`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/profiles/` | Create/update a profile (`username`, `monthly_income`, `safety_buffer`) |
| GET | `/profiles/` | List all profiles |
| GET | `/profiles/<id>/` | Profile detail (incl. bills + cards) |
| POST | `/profiles/<id>/bills/` | Add a bill |
| GET | `/profiles/<id>/bills/` | List bills |
| PATCH | `/profiles/<id>/bills/<bill_id>/` | Update one field or more on a bill |
| DELETE | `/profiles/<id>/bills/<bill_id>/` | Remove a bill |
| POST | `/profiles/<id>/credit-cards/` | Add a credit card |
| GET | `/profiles/<id>/credit-cards/` | List credit cards |
| PATCH | `/profiles/<id>/credit-cards/<card_id>/` | Update one field or more on a card |
| DELETE | `/profiles/<id>/credit-cards/<card_id>/` | Remove a card |
| POST | `/profiles/<id>/payoff-plan/` | Get avalanche allocation + full projection for a given `extra_monthly_payment` |
| POST | `/profiles/<id>/safe-to-sweep-preview/` | Read-only safety math — same as simulate-sweep but doesn't log an event. Meant for a live-updating UI gauge. |
| POST | `/profiles/<id>/simulate-sweep/` | Run one daily sweep (persists a `SweepEvent`): pass `checking_balance` (+ optional `date`) |
| GET | `/profiles/<id>/sweeps/` | Sweep history log |

## Connecting the HTML dashboard

`frontend/autostash.html` (the standalone frontend) can talk to this API
directly from the browser. CORS is wide open in `settings.py` via
`CORS_ALLOW_ALL_ORIGINS = True` so it works whether the HTML file is opened
directly (`file://`) or served from anywhere — tighten this to
`CORS_ALLOWED_ORIGINS` before this goes near production.

1. Run the server: `python manage.py runserver` (defaults to `localhost:8000`)
2. Open `frontend/autostash.html` in a browser
3. In the connection bar at the top, confirm the API base URL is
   `http://localhost:8000/api` and click **Connect**
4. If the server isn't running, or the request fails, the dashboard falls
   back to a local JavaScript simulation of the same math — so it's never
   fully broken, just disconnected from persisted data.


### Example walkthrough

```bash
# 1. Create a profile
curl -X POST localhost:8000/api/profiles/ \
  -H "Content-Type: application/json" \
  -d '{"username": "kizie", "monthly_income": 5000, "safety_buffer": 150}'

# 2. Add bills
curl -X POST localhost:8000/api/profiles/1/bills/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Rent", "amount": 1500, "due_day": 1}'

curl -X POST localhost:8000/api/profiles/1/bills/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Electric", "amount": 80, "due_day": 20}'

# 3. Add credit cards
curl -X POST localhost:8000/api/profiles/1/credit-cards/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Chase Sapphire", "balance": 4200, "apr": 24.99, "min_payment": 90}'

curl -X POST localhost:8000/api/profiles/1/credit-cards/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Amex Blue", "balance": 1800, "apr": 19.99, "min_payment": 45}'

# 4. Simulate today's daily sweep
curl -X POST localhost:8000/api/profiles/1/simulate-sweep/ \
  -H "Content-Type: application/json" \
  -d '{"checking_balance": 2200, "date": "2026-07-18"}'

# 5. Ask for the full optimized payoff plan at $300/month extra
curl -X POST localhost:8000/api/profiles/1/payoff-plan/ \
  -H "Content-Type: application/json" \
  -d '{"extra_monthly_payment": 300}'

# 6. Check sweep history
curl localhost:8000/api/profiles/1/sweeps/
```

## Notes / next steps

- `checking_balance` is passed in per-request to simulate a live bank
  feed (Plaid-style) without wiring up a real bank integration.
- The avalanche method (highest APR first) is used rather than snowball
  (smallest balance first) since it minimizes total interest paid —
  swap the sort in `services.py` if you want snowball instead.
- `AUTOSTASH_MIN_SAFETY_BUFFER` and `AUTOSTASH_MAX_DAILY_SWEEP_FRACTION`
  in `settings.py` control the global safety math and are the first
  knobs to tune.
- No auth is wired up (`AllowAny` in DRF settings) — add
  `IsAuthenticated` + token/session auth before this touches real data.
