"""
Service de scoring de crédit — MicroFinance Platform
=====================================================
Modèles : Random Forest + Régression Logistique (indépendants)
Données : microfinance_credit_dataset.csv (32 574 lignes réelles)

Corrections appliquées :
  1. Les deux modèles s'affichent séparément — le décideur compare et choisit
  2. Indicateur d'accord/désaccord entre les deux modèles
  3. Fallback rule-based supprimé — si pas de modèle → erreur explicite
  4. Données d'entraînement depuis le vrai CSV, pas de données synthétiques
  5. Métriques complètes (F1, précision, rappel, AUC) retournées pour chaque modèle
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, roc_auc_score,
    f1_score, precision_score, recall_score, confusion_matrix
)
import joblib
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Exception personnalisée
# ─────────────────────────────────────────────────────────────────

class ModelNotTrainedError(Exception):
    """Levée quand on tente de scorer sans modèle entraîné."""
    pass


# ─────────────────────────────────────────────────────────────────
# Service principal
# ─────────────────────────────────────────────────────────────────

class CreditScoringService:
    """
    Service ML pour le scoring de crédit.

    Principe :
    - Random Forest et Régression Logistique sont entraînés et affichés séparément
    - Le décideur voit les deux scores et leurs métriques pour faire son choix
    - Un indicateur d'accord mesure la convergence entre les deux modèles
    - Si les modèles divergent fortement → revue humaine obligatoire
    - Sans modèle entraîné, une erreur claire est levée (pas de fallback inventé)
    """

    RF_MODEL_FILE    = 'random_forest_credit.pkl'
    LR_MODEL_FILE    = 'logistic_regression_credit.pkl'
    SCALER_FILE      = 'credit_scaler.pkl'
    METRICS_FILE     = 'model_metrics.pkl'
    DATASET_FILENAME = 'microfinance_credit_dataset.csv'

    # Les 21 features dans l'ordre exact attendu par le modèle
    FEATURES = [
        'age', 'gender_encoded', 'marital_encoded', 'dependents',
        'employment_encoded', 'education_encoded', 'years_employed',
        'monthly_income', 'monthly_expenses', 'disposable_income',
        'debt_to_income_ratio', 'other_loan_outstanding',
        'has_bank_account', 'loan_count', 'active_loans',
        'previous_default_rate', 'avg_days_late',
        'requested_amount', 'loan_duration', 'income_to_loan_ratio',
        'age_income_interaction',
    ]

    # Encodages texte -> nombre
    GENDER_MAP = {'M': 1, 'F': 0}
    MARITAL_MAP = {'single': 0, 'married': 1, 'divorced': 2, 'widowed': 3}
    EMPLOYMENT_MAP = {
        'unemployed': 0, 'retired': 1, 'farmer': 2,
        'self_employed': 3, 'employed': 4, 'business_owner': 5,
    }
    EDUCATION_MAP = {
        'none': 0, 'primary': 1, 'secondary': 2,
        'university': 3, 'postgraduate': 4,
    }

    def __init__(self):
        try:
            from django.conf import settings
            self.model_path   = Path(getattr(settings, 'ML_MODELS_PATH', '/tmp/ml_models'))
            self.dataset_path = Path(settings.BASE_DIR) / self.DATASET_FILENAME
        except Exception:
            self.model_path   = Path('/tmp/ml_models')
            self.dataset_path = Path(self.DATASET_FILENAME)

        self.model_path.mkdir(parents=True, exist_ok=True)

        self.rf_model = None
        self.lr_model = None
        self.scaler   = None
        self.metrics  = {}

        self._load_models()

    # ─────────────────────────────────────────────
    # CHARGEMENT DES MODÈLES SAUVEGARDÉS
    # ─────────────────────────────────────────────

    def _load_models(self):
        """Charge les modèles depuis le disque si disponibles."""
        rf_path      = self.model_path / self.RF_MODEL_FILE
        lr_path      = self.model_path / self.LR_MODEL_FILE
        scaler_path  = self.model_path / self.SCALER_FILE
        metrics_path = self.model_path / self.METRICS_FILE

        if rf_path.exists():
            self.rf_model = joblib.load(rf_path)
        if lr_path.exists():
            self.lr_model = joblib.load(lr_path)
        if scaler_path.exists():
            self.scaler = joblib.load(scaler_path)
        if metrics_path.exists():
            self.metrics = joblib.load(metrics_path)

    @property
    def is_trained(self):
        return self.rf_model is not None and self.lr_model is not None

    # ─────────────────────────────────────────────
    # EXTRACTION DES FEATURES D'UN CLIENT DJANGO
    # ─────────────────────────────────────────────

    def _extract_client_features(self, client, loan_amount=None, loan_duration=None):
        """
        Transforme un objet Client Django en vecteur de 21 nombres.
        """
        monthly_income   = float(client.monthly_income)
        monthly_expenses = float(client.monthly_expenses)
        other_debt       = float(client.other_loan_outstanding)

        disposable_income = monthly_income - monthly_expenses
        dti = (other_debt / (monthly_income * 12)) if monthly_income > 0 else 0.0

        # Historique de prêts depuis la BDD
        all_loans    = client.loans.filter(status__in=['active', 'completed', 'defaulted'])
        loan_count   = all_loans.count()
        active_loans = client.loans.filter(status='active').count()

        default_count         = all_loans.filter(status='defaulted').count()
        previous_default_rate = (default_count / loan_count) if loan_count > 0 else 0.0

        from apps.loans.models import RepaymentSchedule
        past_schedules = RepaymentSchedule.objects.filter(
            loan__client=client, status__in=['paid', 'overdue']
        ).values_list('days_late', flat=True)

        avg_days_late = 0.0
        if past_schedules.exists():
            days_list     = list(past_schedules)
            avg_days_late = sum(days_list) / len(days_list) if days_list else 0.0

        req_amount     = float(loan_amount) if loan_amount else monthly_income * 3
        duration       = int(loan_duration) if loan_duration else 12
        income_to_loan = (monthly_income / req_amount) if req_amount > 0 else 0.0
        age            = client.age
        age_income     = age * monthly_income / 100_000

        return {
            'age':                   age,
            'gender_encoded':        self.GENDER_MAP.get(client.gender, 0),
            'marital_encoded':       self.MARITAL_MAP.get(client.marital_status, 0),
            'dependents':            client.number_of_dependents,
            'employment_encoded':    self.EMPLOYMENT_MAP.get(client.employment_type, 0),
            'education_encoded':     self.EDUCATION_MAP.get(client.education_level, 0),
            'years_employed':        float(client.years_employed),
            'monthly_income':        monthly_income,
            'monthly_expenses':      monthly_expenses,
            'disposable_income':     disposable_income,
            'debt_to_income_ratio':  round(dti, 6),
            'other_loan_outstanding':other_debt,
            'has_bank_account':      int(client.has_bank_account),
            'loan_count':            loan_count,
            'active_loans':          active_loans,
            'previous_default_rate': previous_default_rate,
            'avg_days_late':         avg_days_late,
            'requested_amount':      req_amount,
            'loan_duration':         duration,
            'income_to_loan_ratio':  round(income_to_loan, 6),
            'age_income_interaction':round(age_income, 4),
        }

    # ─────────────────────────────────────────────
    # SCORING D'UN CLIENT
    # ─────────────────────────────────────────────

    def score_client(self, client, loan_amount=None, loan_duration=None):
        """
        Calcule les scores RF et LR séparément et retourne les deux
        avec un indicateur d'accord pour aider le décideur.

        Lève ModelNotTrainedError si les modèles ne sont pas entraînés.
        """
        if not self.is_trained:
            raise ModelNotTrainedError(
                "Aucun modèle entraîné. "
                "Allez dans 'Scoring ML → Entraîner les modèles' avant de scorer un client."
            )

        features       = self._extract_client_features(client, loan_amount, loan_duration)
        feature_vector = np.array([[features[f] for f in self.FEATURES]])

        # ── Random Forest ─────────────────────────
        rf_proba = float(self.rf_model.predict_proba(feature_vector)[0][1])
        rf_risk, rf_rec, rf_color = self._interpret_score(rf_proba)

        # ── Régression Logistique ─────────────────
        scaled   = self.scaler.transform(feature_vector)
        lr_proba = float(self.lr_model.predict_proba(scaled)[0][1])
        lr_risk, lr_rec, lr_color = self._interpret_score(lr_proba)

        # ── Accord entre modèles ──────────────────
        difference = abs(rf_proba - lr_proba)
        if difference < 0.10:
            agreement       = 'fort'
            agreement_label = 'Les deux modèles convergent — décision fiable'
            requires_review = False
        elif difference < 0.25:
            agreement       = 'modéré'
            agreement_label = 'Légère divergence — vérifier les indicateurs financiers'
            requires_review = False
        else:
            agreement       = 'faible'
            agreement_label = 'Désaccord fort entre les modèles — revue humaine obligatoire'
            requires_review = True

        # ── Importance des features (RF) ──────────
        feature_importance = {}
        if hasattr(self.rf_model, 'feature_importances_'):
            raw = dict(zip(self.FEATURES, self.rf_model.feature_importances_.tolist()))
            feature_importance = dict(
                sorted(raw.items(), key=lambda x: x[1], reverse=True)[:10]
            )

        return {
            # Scores Random Forest
            'rf_score':           round(rf_proba, 4),
            'rf_score_pct':       round(rf_proba * 100, 1),
            'rf_risk':            rf_risk,
            'rf_recommendation':  rf_rec,
            'rf_color':           rf_color,
            'rf_metrics':         self.metrics.get('rf', {}),

            # Scores Régression Logistique
            'lr_score':           round(lr_proba, 4),
            'lr_score_pct':       round(lr_proba * 100, 1),
            'lr_risk':            lr_risk,
            'lr_recommendation':  lr_rec,
            'lr_color':           lr_color,
            'lr_metrics':         self.metrics.get('lr', {}),

            # Accord entre modèles
            'agreement':          agreement,
            'agreement_label':    agreement_label,
            'score_difference':   round(difference, 4),
            'requires_review':    requires_review,

            # Détails
            'feature_importance': feature_importance,
            'features':           features,
        }

    # ─────────────────────────────────────────────
    # INTERPRÉTATION D'UN SCORE
    # ─────────────────────────────────────────────

    def _interpret_score(self, score):
        if score >= 0.80:
            return ('Faible',     'Approuver',                'success')
        elif score >= 0.65:
            return ('Modéré',     'Approuver avec conditions', 'info')
        elif score >= 0.50:
            return ('Élevé',      'Étude approfondie requise', 'warning')
        elif score >= 0.35:
            return ('Très élevé', 'Garant obligatoire',        'orange')
        else:
            return ('Critique',   'Refuser',                   'danger')

    # ─────────────────────────────────────────────
    # ENTRAÎNEMENT
    # ─────────────────────────────────────────────

    def train_models(self):
        """
        Entraîne RF et LR sur les données réelles (BDD Django ou CSV Kaggle).
        Retourne les métriques complètes des deux modèles.
        Lève ValueError si données insuffisantes.
        """
        X, y, source = self._load_training_data()

        logger.info(f"Entraînement : {len(X)} exemples (source: {source})")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=42, stratify=y
        )

        # ── Random Forest ─────────────────────────
        self.rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1,
        )
        self.rf_model.fit(X_train, y_train)
        rf_pred  = self.rf_model.predict(X_test)
        rf_proba = self.rf_model.predict_proba(X_test)[:, 1]
        rf_metrics = self._compute_metrics(y_test, rf_pred, rf_proba)

        # ── Régression Logistique ─────────────────
        self.scaler    = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled  = self.scaler.transform(X_test)

        self.lr_model = LogisticRegression(
            C=1.0, max_iter=1000, class_weight='balanced',
            random_state=42, n_jobs=-1,
        )
        self.lr_model.fit(X_train_scaled, y_train)
        lr_pred  = self.lr_model.predict(X_test_scaled)
        lr_proba = self.lr_model.predict_proba(X_test_scaled)[:, 1]
        lr_metrics = self._compute_metrics(y_test, lr_pred, lr_proba)

        # ── Sauvegarde ────────────────────────────
        self.metrics = {'rf': rf_metrics, 'lr': lr_metrics}
        joblib.dump(self.rf_model, self.model_path / self.RF_MODEL_FILE)
        joblib.dump(self.lr_model, self.model_path / self.LR_MODEL_FILE)
        joblib.dump(self.scaler,   self.model_path / self.SCALER_FILE)
        joblib.dump(self.metrics,  self.model_path / self.METRICS_FILE)

        return {
            'source':    source,
            'n_samples': len(X),
            'n_train':   len(X_train),
            'n_test':    len(X_test),
            'n_features':len(self.FEATURES),
            'class_distribution': {
                'bon_payeur':       int(y.sum()),
                'defaut':           int(len(y) - y.sum()),
                'ratio_defaut_pct': round((len(y) - y.sum()) / len(y) * 100, 1),
            },
            'rf': rf_metrics,
            'lr': lr_metrics,
        }

    # ─────────────────────────────────────────────
    # MÉTRIQUES
    # ─────────────────────────────────────────────

    def _compute_metrics(self, y_true, y_pred, y_proba):
        """Calcule F1, précision, rappel, AUC et matrice de confusion."""
        report = classification_report(y_true, y_pred, output_dict=True)
        cm     = confusion_matrix(y_true, y_pred)
        return {
            'auc':       round(float(roc_auc_score(y_true, y_proba)), 4),
            'f1':        round(float(f1_score(y_true, y_pred)), 4),
            'precision': round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
            'recall':    round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
            'accuracy':  round(float(report['accuracy']), 4),
            'class_0': {
                'precision': round(float(report['0']['precision']), 4),
                'recall':    round(float(report['0']['recall']), 4),
                'f1':        round(float(report['0']['f1-score']), 4),
                'support':   int(report['0']['support']),
            },
            'class_1': {
                'precision': round(float(report['1']['precision']), 4),
                'recall':    round(float(report['1']['recall']), 4),
                'f1':        round(float(report['1']['f1-score']), 4),
                'support':   int(report['1']['support']),
            },
            'confusion_matrix': cm.tolist(),
        }

    # ─────────────────────────────────────────────
    # CHARGEMENT DES DONNÉES D'ENTRAÎNEMENT
    # ─────────────────────────────────────────────

    def _load_training_data(self):
        """
        Priorité :
          1. BDD Django (si >= 200 prêts labellisés)
          2. CSV Kaggle adapté
        Lève ValueError si aucune source suffisante.
        """
        X_real, y_real = self._extract_from_database()

        if len(X_real) >= 200:
            return np.array(X_real), np.array(y_real), 'base_de_donnees'

        if self.dataset_path.exists():
            X_csv, y_csv = self._load_from_csv()
            if len(X_csv) >= 200:
                if len(X_real) >= 10:
                    X_mix = np.vstack([np.array(X_real), X_csv])
                    y_mix = np.concatenate([np.array(y_real), y_csv])
                    return X_mix, y_mix, 'mixte_bdd_csv'
                return X_csv, y_csv, 'csv_kaggle'

        raise ValueError(
            f"Données insuffisantes.\n"
            f"  BDD Django  : {len(X_real)} prêts (minimum 200)\n"
            f"  CSV Kaggle  : non trouvé ({self.dataset_path})\n\n"
            f"Placez 'microfinance_credit_dataset.csv' à la racine du projet "
            f"ou attendez d'avoir 200+ prêts dans la BDD."
        )

    def _extract_from_database(self):
        """Extrait les exemples d'entraînement depuis les prêts Django."""
        try:
            from apps.loans.models import Loan
        except Exception:
            return [], []

        X, y = [], []
        loans = Loan.objects.filter(
            status__in=['completed', 'defaulted', 'active']
        ).select_related('client', 'product')

        for loan in loans:
            try:
                features = self._extract_client_features(
                    loan.client,
                    loan_amount=float(loan.approved_amount or loan.requested_amount),
                    loan_duration=loan.duration_months,
                )
                if loan.status == 'completed':
                    label = 1
                elif loan.status == 'defaulted':
                    label = 0
                else:
                    label = 0 if loan.overdue_installments.exists() else 1

                X.append([features[f] for f in self.FEATURES])
                y.append(label)
            except Exception as e:
                logger.debug(f"Prêt {loan.pk} ignoré : {e}")

        return X, y

    def _load_from_csv(self):
        """
        Charge microfinance_credit_dataset.csv et encode les colonnes texte.
        Retourne (X: ndarray, y: ndarray).
        """
        df = pd.read_csv(self.dataset_path)

        if 'loan_repaid' not in df.columns:
            raise ValueError("Colonne 'loan_repaid' absente du CSV.")

        # Encoder les colonnes texte -> nombre
        encodings = {
            'gender':             ('gender_encoded',      self.GENDER_MAP),
            'marital_status':     ('marital_encoded',      self.MARITAL_MAP),
            'employment_type':    ('employment_encoded',   self.EMPLOYMENT_MAP),
            'education_level':    ('education_encoded',    self.EDUCATION_MAP),
            'number_of_dependents':('dependents',          None),
        }
        for csv_col, (feat_name, mapping) in encodings.items():
            if csv_col in df.columns:
                if mapping:
                    df[feat_name] = df[csv_col].map(mapping).fillna(0).astype(int)
                else:
                    df[feat_name] = pd.to_numeric(df[csv_col], errors='coerce').fillna(0).astype(int)

        missing = [f for f in self.FEATURES if f not in df.columns]
        if missing:
            raise ValueError(f"Features manquantes dans le CSV : {missing}")

        df_clean = df[self.FEATURES + ['loan_repaid']].dropna()

        return (
            df_clean[self.FEATURES].values.astype(float),
            df_clean['loan_repaid'].values.astype(int),
        )

    # ─────────────────────────────────────────────
    # STATUT DES MODÈLES
    # ─────────────────────────────────────────────

    def get_model_status(self):
        """Retourne l'état des modèles pour affichage dans le dashboard."""
        return {
            'rf_trained':     self.rf_model is not None,
            'lr_trained':     self.lr_model is not None,
            'both_trained':   self.is_trained,
            'rf_metrics':     self.metrics.get('rf', {}),
            'lr_metrics':     self.metrics.get('lr', {}),
            'dataset_exists': self.dataset_path.exists(),
            'dataset_path':   str(self.dataset_path),
            'model_path':     str(self.model_path),
        }


# Instance singleton
scoring_service = CreditScoringService()
