"""
Tests pour MicroFinance Platform
Couvre : modèles, calculs financiers, scoring ML, vues, API
"""
from django.test import TestCase, Client as TestClient
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import json


# ═══════════════════════════════════════════════
# FIXTURES HELPER
# ═══════════════════════════════════════════════

def make_client(**kwargs):
    from apps.clients.models import Client
    defaults = {
        'first_name': 'Mamadou',
        'last_name': 'Diallo',
        'national_id': f"SN{timezone.now().timestamp():.0f}",
        'date_of_birth': date(1985, 6, 15),
        'gender': 'M',
        'marital_status': 'married',
        'number_of_dependents': 2,
        'phone': '+221 77 123 45 67',
        'address': '12 Rue des Almadies',
        'city': 'Dakar',
        'region': 'Dakar',
        'employment_type': 'employed',
        'monthly_income': Decimal('250000'),
        'monthly_expenses': Decimal('100000'),
        'other_loan_outstanding': Decimal('0'),
        'years_employed': 5,
        'education_level': 'secondary',
        'has_bank_account': True,
    }
    defaults.update(kwargs)
    return Client.objects.create(**defaults)


def make_product(**kwargs):
    from apps.loans.models import LoanProduct
    defaults = {
        'name': 'Prêt Test',
        'min_amount': Decimal('50000'),
        'max_amount': Decimal('2000000'),
        'min_duration_months': 3,
        'max_duration_months': 36,
        'annual_interest_rate': Decimal('24'),
        'processing_fee_rate': Decimal('2'),
        'amortization_type': 'constant',
        'min_credit_score': 0.3,
    }
    defaults.update(kwargs)
    return LoanProduct.objects.create(**defaults)


def make_loan(client, product, **kwargs):
    from apps.loans.models import Loan
    defaults = {
        'client': client,
        'product': product,
        'requested_amount': Decimal('500000'),
        'approved_amount': Decimal('500000'),
        'duration_months': 12,
        'interest_rate': Decimal('2.0000'),
        'processing_fee': Decimal('10000'),
        'insurance_amount': Decimal('0'),
        'purpose': 'Fonds de roulement pour commerce',
        'status': 'active',
        'application_date': date.today() - timedelta(days=60),
        'approval_date': date.today() - timedelta(days=55),
        'disbursement_date': date.today() - timedelta(days=50),
        'first_payment_date': date.today() - timedelta(days=20),
        'maturity_date': date.today() + timedelta(days=315),
    }
    defaults.update(kwargs)
    return Loan.objects.create(**defaults)


# ═══════════════════════════════════════════════
# TESTS MODÈLE CLIENT
# ═══════════════════════════════════════════════

class ClientModelTest(TestCase):

    def setUp(self):
        self.client_obj = make_client()

    def test_full_name(self):
        self.assertEqual(self.client_obj.full_name, 'Mamadou Diallo')

    def test_age_calculation(self):
        age = self.client_obj.age
        self.assertGreater(age, 30)
        self.assertLess(age, 60)

    def test_disposable_income(self):
        expected = 250000 - 100000
        self.assertEqual(self.client_obj.disposable_income, expected)

    def test_debt_to_income_ratio_zero(self):
        self.assertEqual(self.client_obj.debt_to_income_ratio, 0.0)

    def test_debt_to_income_ratio_with_debt(self):
        self.client_obj.other_loan_outstanding = Decimal('600000')
        self.client_obj.save()
        # 600000 / (250000 * 12) = 0.2
        self.assertAlmostEqual(self.client_obj.debt_to_income_ratio, 0.2, places=4)

    def test_credit_score_label_none(self):
        label, color = self.client_obj.credit_score_label
        self.assertEqual(color, 'secondary')

    def test_credit_score_label_excellent(self):
        self.client_obj.credit_score = 0.85
        label, color = self.client_obj.credit_score_label
        self.assertEqual(color, 'success')

    def test_credit_score_label_risk(self):
        self.client_obj.credit_score = 0.25
        label, color = self.client_obj.credit_score_label
        self.assertEqual(color, 'danger')


# ═══════════════════════════════════════════════
# TESTS MODÈLE PRÊT & AMORTISSEMENT
# ═══════════════════════════════════════════════

class LoanAmortizationTest(TestCase):

    def setUp(self):
        self.client_obj = make_client()
        self.product = make_product()
        self.loan = make_loan(self.client_obj, self.product)

    def test_loan_number_generated(self):
        self.assertTrue(self.loan.loan_number.startswith('MF'))
        self.assertEqual(len(self.loan.loan_number), 11)

    def test_amortization_constant_schedule_length(self):
        schedule = self.loan.get_amortization_schedule()
        self.assertEqual(len(schedule), 12)

    def test_amortization_constant_first_row(self):
        schedule = self.loan.get_amortization_schedule()
        first = schedule[0]
        self.assertIn('payment', first)
        self.assertIn('principal', first)
        self.assertIn('interest', first)
        self.assertIn('balance', first)
        # Vérifier que intérêt = principal × taux mensuel
        expected_interest = 500000 * 0.02
        self.assertAlmostEqual(first['interest'], expected_interest, delta=1)

    def test_amortization_constant_balance_zero_at_end(self):
        schedule = self.loan.get_amortization_schedule()
        last_balance = schedule[-1]['balance']
        self.assertAlmostEqual(last_balance, 0, delta=10)

    def test_amortization_constant_payment_equal(self):
        """En amortissement constant, toutes les mensualités sont égales"""
        schedule = self.loan.get_amortization_schedule()
        payments = [r['payment'] for r in schedule]
        self.assertAlmostEqual(max(payments) - min(payments), 0, delta=1)

    def test_amortization_degressive_payment_decreasing(self):
        """En amortissement dégressif, les mensualités diminuent"""
        self.product.amortization_type = 'degressive'
        self.product.save()
        schedule = self.loan.get_amortization_schedule()
        payments = [r['payment'] for r in schedule]
        # Chaque mensualité doit être <= la précédente
        for i in range(1, len(payments)):
            self.assertLessEqual(payments[i], payments[i-1] + 1)

    def test_amortization_degressive_principal_equal(self):
        """En dégressif, le principal remboursé est constant"""
        self.product.amortization_type = 'degressive'
        self.product.save()
        schedule = self.loan.get_amortization_schedule()
        principals = [r['principal'] for r in schedule]
        expected = 500000 / 12
        for p in principals:
            self.assertAlmostEqual(p, expected, delta=1)

    def test_total_interest_positive(self):
        self.assertGreater(self.loan.total_interest, 0)

    def test_total_amount_due_greater_than_principal(self):
        self.assertGreater(self.loan.total_amount_due, float(self.loan.principal))

    def test_principal_property(self):
        self.assertEqual(self.loan.principal, Decimal('500000'))

    def test_monthly_rate(self):
        self.assertAlmostEqual(self.loan.monthly_rate, 0.02, places=4)


# ═══════════════════════════════════════════════
# TESTS ÉCHÉANCIER & PAIEMENTS
# ═══════════════════════════════════════════════

class RepaymentScheduleTest(TestCase):

    def setUp(self):
        self.client_obj = make_client()
        self.product = make_product()
        self.loan = make_loan(
            self.client_obj, self.product,
            first_payment_date=date.today() - timedelta(days=30)
        )
        self.loan.create_repayment_schedule()

    def test_schedule_created(self):
        self.assertEqual(self.loan.schedule.count(), 12)

    def test_schedule_installment_numbers(self):
        numbers = list(self.loan.schedule.values_list('installment_number', flat=True).order_by('installment_number'))
        self.assertEqual(numbers, list(range(1, 13)))

    def test_first_installment_status_pending(self):
        first = self.loan.schedule.order_by('installment_number').first()
        self.assertIn(first.status, ['pending', 'overdue'])

    def test_outstanding_balance_full_before_payment(self):
        balance = self.loan.outstanding_balance
        self.assertAlmostEqual(balance, 500000, delta=1000)

    def test_total_paid_zero_before_payment(self):
        self.assertEqual(self.loan.total_paid, 0)

    def test_overdue_detection(self):
        """Les échéances passées sans paiement doivent être détectées"""
        past_item = self.loan.schedule.filter(
            due_date__lt=date.today()
        ).first()
        if past_item:
            self.assertTrue(past_item.is_overdue)


class PaymentRecordingTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('agent', password='test123')
        self.client_obj = make_client()
        self.product = make_product()
        self.loan = make_loan(
            self.client_obj, self.product,
            first_payment_date=date.today() - timedelta(days=30)
        )
        self.loan.create_repayment_schedule()

    def _record_payment(self, amount):
        from apps.loans.models import Payment
        payment = Payment.objects.create(
            loan=self.loan,
            payment_date=date.today(),
            amount_paid=Decimal(str(amount)),
            principal_paid=Decimal('0'),
            interest_paid=Decimal('0'),
            payment_method='cash',
            collected_by=self.user,
        )
        return payment

    def test_payment_recorded(self):
        p = self._record_payment(45000)
        self.assertEqual(p.loan, self.loan)
        self.assertEqual(float(p.amount_paid), 45000)

    def test_total_paid_after_payment(self):
        self._record_payment(45000)
        self.assertEqual(self.loan.total_paid, 45000)


# ═══════════════════════════════════════════════
# TESTS SCORING ML
# ═══════════════════════════════════════════════

class CreditScoringTest(TestCase):

    def setUp(self):
        self.client_obj = make_client(
            monthly_income=Decimal('300000'),
            monthly_expenses=Decimal('120000'),
            years_employed=7,
            has_bank_account=True,
            other_loan_outstanding=Decimal('0'),
        )

    def test_score_returns_dict(self):
        from apps.scoring.ml_service import scoring_service
        result = scoring_service.score_client(self.client_obj)
        self.assertIsInstance(result, dict)

    def test_score_has_required_keys(self):
        from apps.scoring.ml_service import scoring_service
        result = scoring_service.score_client(self.client_obj)
        required_keys = ['score', 'score_percentage', 'risk_level', 'recommendation', 'color']
        for key in required_keys:
            self.assertIn(key, result)

    def test_score_between_0_and_1(self):
        from apps.scoring.ml_service import scoring_service
        result = scoring_service.score_client(self.client_obj)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 1)

    def test_score_percentage_consistent(self):
        from apps.scoring.ml_service import scoring_service
        result = scoring_service.score_client(self.client_obj)
        self.assertAlmostEqual(
            result['score'] * 100,
            result['score_percentage'],
            places=1
        )

    def test_good_profile_higher_score(self):
        """Un bon profil doit avoir un score plus élevé qu'un profil risqué"""
        from apps.scoring.ml_service import scoring_service
        good_client = make_client(
            national_id='GOOD123',
            monthly_income=Decimal('500000'),
            monthly_expenses=Decimal('100000'),
            years_employed=10,
            has_bank_account=True,
            other_loan_outstanding=Decimal('0'),
        )
        risky_client = make_client(
            national_id='RISKY123',
            monthly_income=Decimal('50000'),
            monthly_expenses=Decimal('45000'),
            years_employed=0,
            has_bank_account=False,
            other_loan_outstanding=Decimal('500000'),
        )
        good_score = scoring_service.score_client(good_client)['score']
        risky_score = scoring_service.score_client(risky_client)['score']
        self.assertGreater(good_score, risky_score)

    def test_risk_level_mapping(self):
        from apps.scoring.ml_service import scoring_service
        result = scoring_service.score_client(self.client_obj)
        valid_levels = ['Faible', 'Modéré', 'Élevé', 'Très élevé', 'Critique']
        self.assertIn(result['risk_level'], valid_levels)

    def test_color_mapping(self):
        from apps.scoring.ml_service import scoring_service
        result = scoring_service.score_client(self.client_obj)
        valid_colors = ['success', 'info', 'warning', 'orange', 'danger']
        self.assertIn(result['color'], valid_colors)

    def test_feature_extraction(self):
        from apps.scoring.ml_service import scoring_service
        features = scoring_service._extract_client_features(self.client_obj)
        self.assertEqual(len(features), len(scoring_service.FEATURES))
        # Vérifier des valeurs connues
        self.assertEqual(features['monthly_income'], 300000)
        self.assertEqual(features['monthly_expenses'], 120000)
        self.assertEqual(features['has_bank_account'], 1)
        self.assertEqual(features['other_loan_outstanding'], 0)

    def test_synthetic_training_data(self):
        from apps.scoring.ml_service import scoring_service
        X, y = scoring_service._generate_synthetic_data(100)
        self.assertEqual(len(X), 100)
        self.assertEqual(len(y), 100)
        self.assertEqual(X.shape[1], len(scoring_service.FEATURES))
        # Labels binaires
        unique = set(y.tolist())
        self.issubset(unique, {0, 1})

    def test_interpret_score_excellent(self):
        from apps.scoring.ml_service import scoring_service
        risk, rec, color = scoring_service._interpret_score(0.85)
        self.assertEqual(color, 'success')

    def test_interpret_score_critical(self):
        from apps.scoring.ml_service import scoring_service
        risk, rec, color = scoring_service._interpret_score(0.20)
        self.assertEqual(color, 'danger')

    def test_score_with_loan_amount(self):
        from apps.scoring.ml_service import scoring_service
        result = scoring_service.score_client(
            self.client_obj,
            loan_amount=1000000,
            loan_duration=24
        )
        self.assertIsInstance(result['score'], float)
        features = result['features']
        self.assertEqual(features['requested_amount'], 1000000)
        self.assertEqual(features['loan_duration'], 24)


# ═══════════════════════════════════════════════
# TESTS VUES (INTÉGRATION)
# ═══════════════════════════════════════════════

class ViewAuthTest(TestCase):
    """Test que les vues nécessitent une authentification"""

    def test_dashboard_redirects_unauthenticated(self):
        response = self.client.get('/')
        self.assertIn(response.status_code, [302, 301])

    def test_clients_redirects_unauthenticated(self):
        response = self.client.get('/clients/')
        self.assertIn(response.status_code, [302, 301])

    def test_loans_redirects_unauthenticated(self):
        response = self.client.get('/loans/')
        self.assertIn(response.status_code, [302, 301])

    def test_login_page_accessible(self):
        response = self.client.get('/auth/login/')
        self.assertEqual(response.status_code, 200)


class DashboardViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('admin', password='admin123')
        self.client.login(username='admin', password='admin123')

    def test_dashboard_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_context_keys(self):
        response = self.client.get('/')
        ctx = response.context
        for key in ['total_clients', 'total_portfolio', 'recovery_rate', 'par_30']:
            self.assertIn(key, ctx)

    def test_portfolio_report_loads(self):
        response = self.client.get('/rapports/portefeuille/')
        self.assertEqual(response.status_code, 200)


class ClientViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('agent', password='test123')
        self.client.login(username='agent', password='test123')
        self.client_obj = make_client()

    def test_client_list_loads(self):
        response = self.client.get('/clients/')
        self.assertEqual(response.status_code, 200)

    def test_client_list_contains_client(self):
        response = self.client.get('/clients/')
        self.assertContains(response, 'Mamadou')

    def test_client_detail_loads(self):
        response = self.client.get(f'/clients/{self.client_obj.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_client_create_get(self):
        response = self.client.get('/clients/nouveau/')
        self.assertEqual(response.status_code, 200)

    def test_client_create_post(self):
        data = {
            'first_name': 'Fatou',
            'last_name': 'Sow',
            'national_id': 'SN99887766',
            'date_of_birth': '1990-03-20',
            'gender': 'F',
            'marital_status': 'single',
            'number_of_dependents': 0,
            'phone': '+221 76 000 00 00',
            'address': '5 Rue Blaise Diagne',
            'city': 'Dakar',
            'region': 'Dakar',
            'employment_type': 'self_employed',
            'monthly_income': '150000',
            'monthly_expenses': '70000',
            'other_loan_outstanding': '0',
            'years_employed': '3',
            'education_level': 'secondary',
            'has_bank_account': True,
        }
        response = self.client.post('/clients/nouveau/', data)
        self.assertEqual(response.status_code, 302)  # Redirect after success

        from apps.clients.models import Client
        self.assertTrue(Client.objects.filter(national_id='SN99887766').exists())

    def test_client_search_filter(self):
        response = self.client.get('/clients/?q=Mamadou')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mamadou')

    def test_client_search_no_result(self):
        response = self.client.get('/clients/?q=XYZInexistant999')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '0')


class LoanViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('agent', password='test123')
        self.client.login(username='agent', password='test123')
        self.client_obj = make_client()
        self.product = make_product()
        self.loan = make_loan(self.client_obj, self.product, status='pending')

    def test_loan_list_loads(self):
        response = self.client.get('/loans/')
        self.assertEqual(response.status_code, 200)

    def test_loan_detail_loads(self):
        response = self.client.get(f'/loans/{self.loan.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_loan_detail_shows_number(self):
        response = self.client.get(f'/loans/{self.loan.pk}/')
        self.assertContains(response, self.loan.loan_number)

    def test_loan_approve_get(self):
        response = self.client.get(f'/loans/{self.loan.pk}/approuver/')
        self.assertEqual(response.status_code, 200)

    def test_loan_approve_post(self):
        data = {
            'approved_amount': '500000',
            'disbursement_date': date.today().isoformat(),
            'first_payment_date': (date.today() + timedelta(days=30)).isoformat(),
            'notes': 'Approuvé après vérification',
        }
        response = self.client.post(f'/loans/{self.loan.pk}/approuver/', data)
        self.assertEqual(response.status_code, 302)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, 'approved')

    def test_loan_reject_post(self):
        data = {'rejection_reason': 'Score insuffisant'}
        response = self.client.post(f'/loans/{self.loan.pk}/rejeter/', data)
        self.assertEqual(response.status_code, 302)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, 'rejected')

    def test_overdue_loans_view(self):
        response = self.client.get('/loans/impayes/')
        self.assertEqual(response.status_code, 200)

    def test_schedule_list_view(self):
        response = self.client.get('/loans/echeanciers/')
        self.assertEqual(response.status_code, 200)


# ═══════════════════════════════════════════════
# TESTS API REST
# ═══════════════════════════════════════════════

class APITest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('api_user', password='test123')
        self.client.login(username='api_user', password='test123')
        self.client_obj = make_client()
        self.product = make_product()

    def test_api_kpis(self):
        response = self.client.get('/api/kpis/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.assertIn('portfolio', data)

    def test_api_client_search(self):
        response = self.client.get('/api/clients/search/?q=Mamadou')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('results', data)

    def test_api_client_search_short_query(self):
        response = self.client.get('/api/clients/search/?q=M')
        data = json.loads(response.content)
        self.assertEqual(data['results'], [])

    def test_api_client_detail(self):
        response = self.client.get(f'/api/clients/{self.client_obj.pk}/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['client']['full_name'], 'Mamadou Diallo')

    def test_api_amortization_constant(self):
        response = self.client.get('/api/amortization/?amount=500000&duration=12&rate=2&type=constant')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['schedule']), 12)
        self.assertAlmostEqual(data['summary']['principal'], 500000)

    def test_api_amortization_invalid(self):
        response = self.client.get('/api/amortization/?amount=0&duration=12&rate=2')
        self.assertEqual(response.status_code, 400)

    def test_api_monthly_trend(self):
        response = self.client.get('/api/trend/?months=6')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['months']), 6)

    def test_api_score_client(self):
        response = self.client.get(f'/api/score/{self.client_obj.pk}/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('score', data)
        self.assertIn('risk_level', data)

    def test_export_loans_csv(self):
        response = self.client.get('/api/export/loans.csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')

    def test_export_clients_csv(self):
        response = self.client.get('/api/export/clients.csv')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])

    def test_api_requires_auth(self):
        # Se déconnecter
        self.client.logout()
        response = self.client.get('/api/kpis/')
        self.assertIn(response.status_code, [302, 403])


# ═══════════════════════════════════════════════
# TESTS GÉNÉRATION PDF
# ═══════════════════════════════════════════════

class PDFGenerationTest(TestCase):

    def setUp(self):
        self.client_obj = make_client()
        self.product = make_product()
        self.loan = make_loan(
            self.client_obj, self.product,
            status='active',
            approved_amount=Decimal('500000'),
        )

    def test_pdf_buffer_generated(self):
        from apps.documents.pdf_service import LoanContractGenerator
        gen = LoanContractGenerator(self.loan)
        buf = gen.generate()
        content = buf.read()
        # PDF commence par %PDF
        self.assertTrue(content.startswith(b'%PDF'))

    def test_pdf_non_empty(self):
        from apps.documents.pdf_service import LoanContractGenerator
        gen = LoanContractGenerator(self.loan)
        buf = gen.generate()
        self.assertGreater(len(buf.read()), 1000)

    def test_generate_loan_contract_saves_file(self):
        import os
        from apps.documents.pdf_service import generate_loan_contract
        filepath, media_path = generate_loan_contract(self.loan)
        self.assertTrue(os.path.exists(filepath))
        self.assertGreater(os.path.getsize(filepath), 0)
        os.remove(filepath)


# ═══════════════════════════════════════════════
# TESTS CALCULS FINANCIERS
# ═══════════════════════════════════════════════

class FinancialCalculationsTest(TestCase):

    def test_constant_amortization_formula(self):
        """Vérifie la formule d'amortissement constant (annuité)"""
        P = 1_000_000  # Principal
        r = 0.02       # Taux mensuel 2%
        n = 12         # 12 mois

        # Formule : M = P * r*(1+r)^n / ((1+r)^n - 1)
        expected_monthly = P * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

        from apps.loans.models import LoanProduct, Loan
        from apps.clients.models import Client

        client = make_client(national_id='CALCTEST01')
        product = make_product(annual_interest_rate=Decimal('24'))
        loan = make_loan(
            client, product,
            requested_amount=Decimal(str(P)),
            approved_amount=Decimal(str(P)),
            duration_months=n,
            interest_rate=Decimal('2.0000'),
        )
        schedule = loan.get_amortization_schedule()
        actual_monthly = schedule[0]['payment']

        self.assertAlmostEqual(actual_monthly, expected_monthly, delta=1)

    def test_degressive_principal_constant(self):
        """En dégressif, le principal est constant à chaque échéance"""
        P = 600_000
        n = 12

        client = make_client(national_id='CALCTEST02')
        product = make_product(amortization_type='degressive')
        loan = make_loan(
            client, product,
            requested_amount=Decimal(str(P)),
            approved_amount=Decimal(str(P)),
            duration_months=n,
        )
        schedule = loan.get_amortization_schedule()
        expected_principal = P / n

        for row in schedule:
            self.assertAlmostEqual(row['principal'], expected_principal, delta=1)

    def test_total_principal_equals_loan_amount(self):
        """La somme des capitaux remboursés doit égaler le montant du prêt"""
        client = make_client(national_id='CALCTEST03')
        product = make_product()
        loan = make_loan(client, product, approved_amount=Decimal('750000'))

        schedule = loan.get_amortization_schedule()
        total_principal = sum(row['principal'] for row in schedule)

        self.assertAlmostEqual(total_principal, 750000, delta=10)

    def test_interest_decreases_in_constant_amortization(self):
        """En amortissement constant, les intérêts diminuent à chaque échéance"""
        client = make_client(national_id='CALCTEST04')
        product = make_product()
        loan = make_loan(client, product)

        schedule = loan.get_amortization_schedule()
        interests = [row['interest'] for row in schedule]

        for i in range(1, len(interests)):
            self.assertLess(interests[i], interests[i-1])

    def test_zero_interest_rate(self):
        """Avec taux zéro, mensualité = principal / durée"""
        client = make_client(national_id='CALCTEST05')
        product = make_product(annual_interest_rate=Decimal('0'))
        loan = make_loan(
            client, product,
            approved_amount=Decimal('120000'),
            duration_months=12,
            interest_rate=Decimal('0'),
        )
        schedule = loan.get_amortization_schedule()
        expected_payment = 120000 / 12

        for row in schedule:
            self.assertAlmostEqual(row['payment'], expected_payment, delta=1)
            self.assertAlmostEqual(row['interest'], 0, delta=1)

    def test_par_contribution_zero_for_no_overdue(self):
        """Un prêt sans retard ne contribue pas au PAR"""
        client = make_client(national_id='CALCTEST06')
        product = make_product()
        loan = make_loan(client, product)
        # Pas de retard
        self.assertEqual(loan.par_contribution, 0)

    def test_recovery_rate_zero_before_payment(self):
        client = make_client(national_id='CALCTEST07')
        product = make_product()
        loan = make_loan(client, product, approved_amount=Decimal('500000'))
        loan.create_repayment_schedule()
        self.assertEqual(loan.recovery_rate, 0)


# ═══════════════════════════════════════════════
# TESTS ALERTES
# ═══════════════════════════════════════════════

class AlertTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('agent', password='test123')
        self.client_obj = make_client()
        self.product = make_product()
        self.loan = make_loan(self.client_obj, self.product)

    def test_create_alert(self):
        from apps.alerts.models import Alert
        alert = Alert.objects.create(
            alert_type='overdue',
            severity='warning',
            title='Test alerte',
            message='Prêt en retard',
            loan=self.loan,
            client=self.client_obj,
        )
        self.assertFalse(alert.is_resolved)
        self.assertEqual(alert.severity_color, 'warning')

    def test_alert_severity_icons(self):
        from apps.alerts.models import Alert
        for severity, expected_icon in [('info', '💡'), ('warning', '⚠️'), ('critical', '🚨')]:
            alert = Alert(severity=severity)
            self.assertEqual(alert.severity_icon, expected_icon)

    def test_resolve_alert(self):
        from apps.alerts.models import Alert
        alert = Alert.objects.create(
            alert_type='system', severity='info',
            title='Test', message='Test',
        )
        self.client.login(username='agent', password='test123')
        response = self.client.get(f'/alertes/{alert.pk}/resoudre/')
        self.assertEqual(response.status_code, 302)
        alert.refresh_from_db()
        self.assertTrue(alert.is_resolved)
