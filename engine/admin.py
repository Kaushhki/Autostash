from django.contrib import admin

from .models import Bill, CreditCard, Profile, SweepEvent


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'monthly_income', 'safety_buffer', 'created_at')


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('name', 'profile', 'amount', 'due_day', 'is_recurring')


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ('name', 'profile', 'balance', 'apr', 'min_payment')


@admin.register(SweepEvent)
class SweepEventAdmin(admin.ModelAdmin):
    list_display = ('profile', 'date', 'checking_balance', 'amount_swept')
    list_filter = ('date',)
