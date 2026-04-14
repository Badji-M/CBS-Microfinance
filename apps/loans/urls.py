from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    path('', views.loan_list, name='list'),
    path('nouveau/', views.loan_create, name='create'),
    path('echeanciers/', views.schedule_list, name='schedule_list'),
    path('paiements/', views.payments_list, name='payments'),
    path('impayes/', views.overdue_loans, name='overdue'),
    path('apercu-amortissement/', views.amortization_preview, name='amortization_preview'),
    path('<int:pk>/', views.loan_detail, name='detail'),
    path('<int:pk>/approuver/', views.loan_approve, name='approve'),
    path('<int:pk>/rejeter/', views.loan_reject, name='reject'),
    path('<int:pk>/decaisser/', views.loan_disburse, name='disburse'),
    path('<int:pk>/paiement/', views.record_payment, name='payment'),
    # Products
    path('produits/', views.product_list, name='product_list'),
    path('produits/nouveau/', views.product_create, name='product_create'),
    path('produits/<int:pk>/modifier/', views.product_edit, name='product_edit'),
]
