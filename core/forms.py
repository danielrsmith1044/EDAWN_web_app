from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Goal, ContactAttempt, VisitNote


class RegisterForm(UserCreationForm):
    email      = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=False)
    last_name  = forms.CharField(max_length=50, required=False)

    class Meta:
        model  = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email      = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name  = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user


class ContactAttemptForm(forms.ModelForm):
    class Meta:
        model  = ContactAttempt
        fields = ('method', 'notes')
        widgets = {
            'method': forms.Select(attrs={'class': 'form-select'}),
            'notes':  forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'What happened? (optional)',
            }),
        }


class VisitNoteForm(forms.ModelForm):
    class Meta:
        model  = VisitNote
        fields = ('notes', 'follow_up_needed', 'follow_up_notes')
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5,
                'placeholder': 'What did you find out during the visit?',
            }),
            'follow_up_needed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_notes':  forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Describe the follow-up needed (optional)',
            }),
        }
        labels = {
            'notes':            'Visit Notes',
            'follow_up_needed': 'Follow-up needed?',
            'follow_up_notes':  'Follow-up Details',
        }


class GoalProgressForm(forms.ModelForm):
    class Meta:
        model  = Goal
        fields = ('current_value',)
        widgets = {
            'current_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {'current_value': 'Current Progress'}


class CompanyCSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        help_text=(
            'Required column: <strong>name</strong>. '
            'Optional: address, city, state, zip_code, phone, email, website, '
            'industry, primary_contact_name, primary_contact_title, notes'
        ),
        widget=forms.FileInput(attrs={'accept': '.csv', 'class': 'form-control'}),
    )
    overwrite_existing = forms.BooleanField(
        required=False,
        initial=False,
        label='Update existing companies by name',
        help_text='If checked, companies with matching names will be updated rather than skipped.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
