from django.urls import path

from . import views

urlpatterns = [
    path('profiles/', views.ProfileListCreateView.as_view(), name='profile-list-create'),
    path('profiles/<int:pk>/', views.ProfileDetailView.as_view(), name='profile-detail'),
    path('profiles/<int:pk>/bills/', views.BillListCreateView.as_view(), name='bill-list-create'),
    path('profiles/<int:pk>/bills/<int:bill_id>/', views.BillDetailView.as_view(), name='bill-detail'),
    path('profiles/<int:pk>/credit-cards/', views.CreditCardListCreateView.as_view(), name='card-list-create'),
    path('profiles/<int:pk>/credit-cards/<int:card_id>/', views.CreditCardDetailView.as_view(), name='card-detail'),
    path('profiles/<int:pk>/payoff-plan/', views.PayoffPlanView.as_view(), name='payoff-plan'),
    path('profiles/<int:pk>/simulate-sweep/', views.SimulateSweepView.as_view(), name='simulate-sweep'),
    path('profiles/<int:pk>/safe-to-sweep-preview/', views.SafeToSweepPreviewView.as_view(), name='safe-to-sweep-preview'),
    path('profiles/<int:pk>/sweeps/', views.SweepHistoryView.as_view(), name='sweep-history'),
]
