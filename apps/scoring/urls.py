from django.urls import path
from . import views

app_name = 'scoring'

urlpatterns = [
    path('', views.scoring_dashboard, name='dashboard'),
    path('entrainer/', views.train_model, name='train'),
    path('batch/', views.batch_score, name='batch_score'),
    path('client/<int:pk>/', views.score_client_view, name='score_client'),
]
