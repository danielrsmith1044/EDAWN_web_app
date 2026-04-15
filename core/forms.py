from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Assignment, Company, ContactAttempt, InviteCode, VisitNote, Message, Reply


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class RegisterForm(UserCreationForm):
    email       = forms.EmailField(required=True)
    first_name  = forms.CharField(max_length=50, required=False)
    last_name   = forms.CharField(max_length=50, required=False)
    invite_code = forms.CharField(
        max_length=40,
        help_text="Enter the invite code provided by your admin.",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Invite code'}),
    )

    class Meta:
        model  = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_invite_code(self):
        code = self.cleaned_data['invite_code'].strip()
        try:
            invite = InviteCode.objects.get(code=code)
        except InviteCode.DoesNotExist:
            raise forms.ValidationError("Invalid invite code.")
        if not invite.is_available:
            raise forms.ValidationError("This invite code has already been used.")
        self._invite = invite
        return code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email      = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name  = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
            # Mark invite code as used
            from django.utils import timezone
            self._invite.used_by = user
            self._invite.used_at = timezone.now()
            self._invite.save(update_fields=['used_by', 'used_at'])
        return user


# ---------------------------------------------------------------------------
# Company Visitation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class MessageForm(forms.ModelForm):
    class Meta:
        model  = Message
        fields = ('subject', 'body', 'is_private')
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject',
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5,
                'placeholder': 'Write your message...',
            }),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_private': 'Send as private message to admin',
        }


class ReplyForm(forms.ModelForm):
    class Meta:
        model  = Reply
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Write a reply...',
            }),
        }
        labels = {'body': ''}


# ---------------------------------------------------------------------------
# Admin (portal-side)
# ---------------------------------------------------------------------------

class QuickCompanyForm(forms.ModelForm):
    class Meta:
        model  = Company
        fields = ('name', 'industry', 'city', 'state', 'phone', 'email',
                  'primary_contact_name')
        widgets = {
            'name':                 forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company name'}),
            'industry':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Industry'}),
            'city':                 forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state':                forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'phone':                forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone'}),
            'email':                forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'primary_contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact name'}),
        }


class QuickAssignForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(status=Company.STATUS_UNASSIGNED),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='Select a company...',
    )
    volunteer = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, is_staff=False),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='Select a volunteer...',
    )


# ---------------------------------------------------------------------------
# Admin (Django admin)
# ---------------------------------------------------------------------------

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
