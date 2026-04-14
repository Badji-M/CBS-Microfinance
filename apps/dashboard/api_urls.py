from django.urls import path
from . import views, api_views

urlpatterns = [
    # Dashboard
    path('chart-data/', views.api_chart_data, name='chart_data'),
    path('kpis/', api_views.api_dashboard_kpis, name='api_kpis'),
    path('trend/', api_views.api_monthly_trend, name='api_trend'),

    # Clients
    path('clients/search/', api_views.api_client_search, name='api_client_search'),
    path('clients/<int:pk>/', api_views.api_client_detail, name='api_client_detail'),

    # Loans
    path('loans/<int:pk>/', api_views.api_loan_detail, name='api_loan_detail'),
    path('amortization/', api_views.api_amortization, name='api_amortization'),

    # Scoring
    path('score/<int:pk>/', api_views.api_score_client, name='api_score_client'),

    # Exports CSV
    path('export/loans.csv', api_views.api_export_loans_csv, name='export_loans_csv'),
    path('export/clients.csv', api_views.api_export_clients_csv, name='export_clients_csv'),
    path('export/schedule/<int:loan_pk>.csv', api_views.api_export_schedule_csv, name='export_schedule_csv'),
]
