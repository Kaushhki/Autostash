"""
Core AutoStash decision engine.

Two jobs live here:

1. Cash-flow safety math — how much can we *safely* sweep out of checking
   today without risking an overdraft on an upcoming bill?
2. Debt avalanche optimization — given a pool of swept cash, which
   credit card(s) should it go to, and what does the full payoff
   trajectory look like?

Pandas is used for the tabular reasoning over bills / cards, since it
makes the sorting, cumulative-sum overflow logic, and month-by-month
amortization simulation both easy to read and easy to extend.
"""
import calendar
from datetime import timedelta
from decimal import Decimal

import pandas as pd
from django.conf import settings


BILL_LOOKAHEAD_DAYS = 5  # how far ahead we protect cash for upcoming bills


def _safety_buffer(profile):
    if profile.safety_buffer is not None:
        return Decimal(profile.safety_buffer)
    return Decimal(str(settings.AUTOSTASH_MIN_SAFETY_BUFFER))


def _upcoming_bills_total(profile, as_of_date, lookahead_days=BILL_LOOKAHEAD_DAYS):
    """Sum of bills whose due_day falls within the lookahead window,
    using Pandas to handle the month-wraparound logic cleanly."""
    bills = list(profile.bills.filter(is_recurring=True).values('name', 'amount', 'due_day'))
    if not bills:
        return Decimal('0'), []

    df = pd.DataFrame(bills)
    days_in_month = calendar.monthrange(as_of_date.year, as_of_date.month)[1]

    def days_until_due(due_day):
        due_day = min(int(due_day), days_in_month)
        delta = due_day - as_of_date.day
        if delta < 0:
            # already passed this month -> due next month, far away
            delta += days_in_month
        return delta

    df['days_until_due'] = df['due_day'].apply(days_until_due)
    upcoming = df[df['days_until_due'] <= lookahead_days].copy()
    upcoming['amount'] = upcoming['amount'].astype(float)

    total = Decimal(str(upcoming['amount'].sum())) if not upcoming.empty else Decimal('0')
    breakdown = upcoming[['name', 'amount', 'days_until_due']].to_dict(orient='records')
    return total, breakdown


def calculate_safe_to_sweep(profile, checking_balance, as_of_date):
    """
    Returns (safe_amount: Decimal, breakdown: dict).

    Safety math:
      safe = checking_balance
             - safety_buffer
             - upcoming_bills_due_within_lookahead_window
      capped at AUTOSTASH_MAX_DAILY_SWEEP_FRACTION * checking_balance
      floored at 0
    """
    checking_balance = Decimal(str(checking_balance))
    buffer_amt = _safety_buffer(profile)
    bills_total, bills_breakdown = _upcoming_bills_total(profile, as_of_date)

    raw_safe = checking_balance - buffer_amt - bills_total
    cap = checking_balance * Decimal(str(settings.AUTOSTASH_MAX_DAILY_SWEEP_FRACTION))

    safe_amount = max(Decimal('0'), min(raw_safe, cap))

    breakdown = {
        'checking_balance': float(checking_balance),
        'safety_buffer': float(buffer_amt),
        'upcoming_bills_total': float(bills_total),
        'upcoming_bills_detail': bills_breakdown,
        'lookahead_days': BILL_LOOKAHEAD_DAYS,
        'raw_safe_amount': float(raw_safe),
        'daily_sweep_cap': float(cap),
        'final_safe_to_sweep': float(safe_amount),
    }
    return safe_amount, breakdown


def allocate_avalanche(cards_qs, extra_payment):
    """
    Debt avalanche allocation: sort cards highest-APR-first, dump the
    extra payment into the top card, overflow (if it exceeds that
    card's balance) cascades to the next-highest APR card.

    Returns dict {card_id: amount_allocated (Decimal)}.
    """
    cards = list(cards_qs.values('id', 'name', 'balance', 'apr'))
    if not cards or extra_payment <= 0:
        return {}

    df = pd.DataFrame(cards)
    df['balance'] = df['balance'].astype(float)
    df['apr'] = df['apr'].astype(float)
    df = df.sort_values('apr', ascending=False).reset_index(drop=True)

    remaining = float(extra_payment)
    allocations = {}
    for _, row in df.iterrows():
        if remaining <= 0:
            break
        pay = min(remaining, row['balance'])
        if pay > 0:
            allocations[int(row['id'])] = Decimal(str(round(pay, 2)))
            remaining -= pay

    return allocations


def full_avalanche_projection(cards_qs, monthly_extra_payment, max_months=600):
    """
    Simulates the complete avalanche payoff schedule month-by-month
    (minimum payments on every card + all extra payment dumped into the
    highest-APR card, cascading as cards get paid off).

    Returns a dict summary: months_to_payoff, total_interest_paid,
    payoff_order (list of card names in the order they get paid off).
    """
    cards = list(cards_qs.values('id', 'name', 'balance', 'apr', 'min_payment'))
    if not cards:
        return {
            'months_to_payoff': 0,
            'total_interest_paid': 0.0,
            'payoff_order': [],
        }

    df = pd.DataFrame(cards)
    df['balance'] = df['balance'].astype(float)
    df['apr'] = df['apr'].astype(float)
    df['min_payment'] = df['min_payment'].astype(float)
    df = df.sort_values('apr', ascending=False).reset_index(drop=True)

    balances = df.set_index('id')['balance'].to_dict()
    min_payments = df.set_index('id')['min_payment'].to_dict()
    monthly_rates = (df.set_index('id')['apr'] / 100.0 / 12.0).to_dict()
    apr_order = list(df['id'])  # highest APR first, fixed avalanche priority
    names = df.set_index('id')['name'].to_dict()

    total_interest = 0.0
    payoff_order = []
    months = 0

    while any(bal > 0.01 for bal in balances.values()) and months < max_months:
        months += 1
        extra_pool = float(monthly_extra_payment)

        # 1. accrue interest, apply minimum payments
        for cid in apr_order:
            if balances[cid] <= 0:
                continue
            interest = balances[cid] * monthly_rates[cid]
            total_interest += interest
            balances[cid] += interest
            pay = min(min_payments[cid], balances[cid])
            balances[cid] -= pay

        # 2. cascade the extra payment pool into highest-APR remaining card
        for cid in apr_order:
            if extra_pool <= 0:
                break
            if balances[cid] <= 0:
                continue
            pay = min(extra_pool, balances[cid])
            balances[cid] -= pay
            extra_pool -= pay

        # 3. track newly-paid-off cards, in order
        for cid in apr_order:
            if balances[cid] <= 0.01 and names[cid] not in payoff_order:
                payoff_order.append(names[cid])

    return {
        'months_to_payoff': months if months < max_months else None,
        'total_interest_paid': round(total_interest, 2),
        'payoff_order': payoff_order,
    }
