from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    """Financial profile for a single AutoStash user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2)
    # Optional per-user override of the global safety buffer setting.
    safety_buffer = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile<{self.user.username}>"


class Bill(models.Model):
    """A recurring monthly bill (rent, utilities, subscriptions, etc.)."""

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='bills')
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_day = models.PositiveSmallIntegerField(help_text="Day of month the bill is due (1-31)")
    is_recurring = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (${self.amount} due day {self.due_day})"


class CreditCard(models.Model):
    """A credit card debt to be paid down."""

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='credit_cards')
    name = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    apr = models.DecimalField(max_digits=5, decimal_places=2, help_text="Annual percentage rate, e.g. 24.99")
    min_payment = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.name} (${self.balance} @ {self.apr}% APR)"


class SweepEvent(models.Model):
    """A logged record of a simulated daily 'money pull' sweep."""

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='sweeps')
    date = models.DateField()
    checking_balance = models.DecimalField(max_digits=12, decimal_places=2)
    amount_swept = models.DecimalField(max_digits=12, decimal_places=2)
    allocations = models.JSONField(help_text="Map of credit_card_id -> amount allocated")
    safety_breakdown = models.JSONField(help_text="Transparency breakdown of the safe-to-sweep math")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Sweep<{self.profile.user.username}, {self.date}, ${self.amount_swept}>"
