from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Bill, CreditCard, Profile, SweepEvent


class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = ['id', 'name', 'amount', 'due_day', 'is_recurring']


class CreditCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditCard
        fields = ['id', 'name', 'balance', 'apr', 'min_payment']


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    bills = BillSerializer(many=True, read_only=True)
    credit_cards = CreditCardSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'username', 'monthly_income', 'safety_buffer', 'bills', 'credit_cards', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        username = validated_data.pop('username')
        user, _ = User.objects.get_or_create(username=username)
        profile, _ = Profile.objects.update_or_create(user=user, defaults=validated_data)
        return profile


class SweepEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SweepEvent
        fields = ['id', 'date', 'checking_balance', 'amount_swept', 'allocations', 'safety_breakdown', 'created_at']
        read_only_fields = fields


class SimulateSweepInputSerializer(serializers.Serializer):
    checking_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    date = serializers.DateField(required=False)


class PayoffPlanInputSerializer(serializers.Serializer):
    extra_monthly_payment = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
