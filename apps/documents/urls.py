from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.document_list, name='list'),
    path('generer/<int:loan_pk>/', views.generate_contract, name='generate'),
    path('telecharger/<int:loan_pk>/', views.download_contract, name='download'),
]
