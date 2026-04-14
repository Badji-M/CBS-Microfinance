from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    path('', views.alert_list, name='list'),
    path('<int:pk>/resoudre/', views.resolve_alert, name='resolve'),
]
