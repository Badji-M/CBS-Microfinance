from django import forms
from .models import Loan, LoanProduct, Payment, Guarantor


class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = [
            'client', 'product', 'requested_amount', 'duration_months',
            'purpose', 'collateral_description', 'collateral_value', 'notes'
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'requested_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1000'}),
            'duration_months': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'collateral_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'collateral_value': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = LoanProduct.objects.filter(is_active=True)
        self.fields['collateral_description'].required = False
        self.fields['collateral_value'].required = False
        self.fields['notes'].required = False


class LoanApprovalForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['approved_amount', 'disbursement_date', 'first_payment_date', 'notes']
        widgets = {
            'approved_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'disbursement_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'first_payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class LoanRejectionForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['rejection_reason']
        widgets = {
            'rejection_reason': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Motif détaillé du rejet...'
            })
        }
        labels = {'rejection_reason': 'Motif de rejet'}


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payment_date', 'amount_paid', 'payment_method', 'reference', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '100'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Réf. transaction...'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import datetime
        self.fields['payment_date'].initial = datetime.date.today()
        self.fields['reference'].required = False
        self.fields['notes'].required = False


class GuarantorForm(forms.ModelForm):
    class Meta:
        model = Guarantor
        fields = '__all__'
        widgets = {
            field: forms.TextInput(attrs={'class': 'form-control'})
            for field in ['full_name', 'national_id', 'phone', 'relationship']
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['address'].widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
        self.fields['monthly_income'].widget = forms.NumberInput(attrs={'class': 'form-control'})


class LoanProductForm(forms.ModelForm):
    class Meta:
        model = LoanProduct
        exclude = ['created_at']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'amortization_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.setdefault('class', 'form-control')
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'


class LoanFilterForm(forms.Form):
    STATUS_CHOICES = [('', 'Tous les statuts')] + list(Loan.STATUS_CHOICES)

    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False,
                                widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-sm',
        'placeholder': 'N° prêt, client...'
    }))
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={
        'type': 'date', 'class': 'form-control form-control-sm'
    }))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={
        'type': 'date', 'class': 'form-control form-control-sm'
    }))
