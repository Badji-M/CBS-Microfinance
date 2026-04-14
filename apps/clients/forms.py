from django import forms
from .models import Client, ClientDocument


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        exclude = ['credit_score', 'credit_score_updated_at', 'created_at', 'updated_at']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'registration_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput,
                                         forms.NumberInput, forms.Select,
                                         forms.Textarea, forms.DateInput)):
                field.widget.attrs.setdefault('class', 'form-control')
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'


class ClientSearchForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Nom, téléphone, CNI...'
    }))
    employment_type = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous les types')] + Client.EMPLOYMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    city = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Ville...'
    }))
    is_active = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous'), ('true', 'Actifs'), ('false', 'Inactifs')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ClientDocumentForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = ['doc_type', 'file', 'description']
        widgets = {
            'doc_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }
