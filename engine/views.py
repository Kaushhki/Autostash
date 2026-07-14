from datetime import date as date_cls

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Bill, CreditCard, Profile, SweepEvent
from .serializers import (
    BillSerializer,
    CreditCardSerializer,
    PayoffPlanInputSerializer,
    ProfileSerializer,
    SimulateSweepInputSerializer,
    SweepEventSerializer,
)


class ProfileListCreateView(APIView):
    """POST to create/update a user's financial profile. GET to list all."""

    def get(self, request):
        profiles = Profile.objects.all()
        return Response(ProfileSerializer(profiles, many=True).data)

    def post(self, request):
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(ProfileSerializer(profile).data, status=status.HTTP_201_CREATED)


class ProfileDetailView(APIView):
    def get(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        return Response(ProfileSerializer(profile).data)


class BillListCreateView(APIView):
    def get(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        return Response(BillSerializer(profile.bills.all(), many=True).data)

    def post(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        serializer = BillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(profile=profile)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BillDetailView(APIView):
    def patch(self, request, pk, bill_id):
        profile = get_object_or_404(Profile, pk=pk)
        bill = get_object_or_404(Bill, pk=bill_id, profile=profile)
        serializer = BillSerializer(bill, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk, bill_id):
        profile = get_object_or_404(Profile, pk=pk)
        bill = get_object_or_404(Bill, pk=bill_id, profile=profile)
        bill.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CreditCardListCreateView(APIView):
    def get(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        return Response(CreditCardSerializer(profile.credit_cards.all(), many=True).data)

    def post(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        serializer = CreditCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(profile=profile)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CreditCardDetailView(APIView):
    def patch(self, request, pk, card_id):
        profile = get_object_or_404(Profile, pk=pk)
        card = get_object_or_404(CreditCard, pk=card_id, profile=profile)
        serializer = CreditCardSerializer(card, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk, card_id):
        profile = get_object_or_404(Profile, pk=pk)
        card = get_object_or_404(CreditCard, pk=card_id, profile=profile)
        card.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SafeToSweepPreviewView(APIView):
    """
    Same safety math as SimulateSweepView, but read-only — does not
    create a SweepEvent. Meant for a live UI gauge that recalculates
    on every keystroke without polluting the sweep history log.
    """

    def post(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        input_serializer = SimulateSweepInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        checking_balance = input_serializer.validated_data['checking_balance']
        as_of_date = input_serializer.validated_data.get('date') or date_cls.today()

        safe_amount, breakdown = services.calculate_safe_to_sweep(profile, checking_balance, as_of_date)

        return Response({
            'amount_safe_to_sweep': float(safe_amount),
            'breakdown': breakdown,
        })


class PayoffPlanView(APIView):
    """
    Computes the optimal (debt avalanche) payoff plan for a user's
    current credit cards: how a given extra monthly payment should be
    allocated right now, plus a full month-by-month projection of the
    entire payoff trajectory.
    """

    def post(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        input_serializer = PayoffPlanInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        extra_payment = input_serializer.validated_data['extra_monthly_payment']

        allocation = services.allocate_avalanche(profile.credit_cards.all(), extra_payment)
        projection = services.full_avalanche_projection(profile.credit_cards.all(), extra_payment)

        cards_by_id = {c.id: c for c in profile.credit_cards.all()}
        allocation_detail = [
            {'credit_card_id': cid, 'name': cards_by_id[cid].name, 'amount_allocated': float(amt)}
            for cid, amt in allocation.items()
        ]

        return Response({
            'profile_id': profile.id,
            'extra_monthly_payment': float(extra_payment),
            'this_period_allocation': allocation_detail,
            'full_projection': projection,
        })


class SimulateSweepView(APIView):
    """
    The core AutoStash behavior: given today's checking account
    balance, calculates how much cash is safe to sweep without risking
    an overdraft on upcoming bills, then allocates that swept cash to
    the optimal credit card (debt avalanche) and logs the event.
    """

    def post(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        input_serializer = SimulateSweepInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        checking_balance = input_serializer.validated_data['checking_balance']
        as_of_date = input_serializer.validated_data.get('date') or date_cls.today()

        safe_amount, breakdown = services.calculate_safe_to_sweep(profile, checking_balance, as_of_date)
        allocation = services.allocate_avalanche(profile.credit_cards.all(), safe_amount)

        cards_by_id = {c.id: c for c in profile.credit_cards.all()}
        allocation_detail = [
            {'credit_card_id': cid, 'name': cards_by_id[cid].name, 'amount_allocated': float(amt)}
            for cid, amt in allocation.items()
        ]

        sweep = SweepEvent.objects.create(
            profile=profile,
            date=as_of_date,
            checking_balance=checking_balance,
            amount_swept=safe_amount,
            allocations={str(cid): float(amt) for cid, amt in allocation.items()},
            safety_breakdown=breakdown,
        )

        return Response({
            'sweep_id': sweep.id,
            'date': str(as_of_date),
            'amount_swept': float(safe_amount),
            'allocation': allocation_detail,
            'safety_breakdown': breakdown,
        }, status=status.HTTP_201_CREATED)


class SweepHistoryView(APIView):
    def get(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        sweeps = profile.sweeps.all()
        return Response(SweepEventSerializer(sweeps, many=True).data)
