from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Assignment, Company, ContactAttempt, InviteCode, VisitNote, Message, Reply

_fc = {'class': 'form-control'}
_fs = {'class': 'form-select'}


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


class CompanyContactUpdateForm(forms.ModelForm):
    """Prefilled from the Company record; saved back on visit submission."""
    class Meta:
        model  = Company
        fields = ('primary_contact_name', 'primary_contact_title', 'phone', 'email')
        widgets = {
            'primary_contact_name':  forms.TextInput(attrs={**_fc, 'placeholder': 'Contact name'}),
            'primary_contact_title': forms.TextInput(attrs={**_fc, 'placeholder': 'Title'}),
            'phone': forms.TextInput(attrs={**_fc, 'placeholder': 'Phone'}),
            'email': forms.EmailInput(attrs={**_fc, 'placeholder': 'Email'}),
        }
        labels = {
            'primary_contact_name':  'Name',
            'primary_contact_title': 'Title',
            'phone': 'Phone',
            'email': 'Email',
        }


class VisitNoteForm(forms.ModelForm):
    class Meta:
        model  = VisitNote
        fields = (
            # Contact
            'contact_name',
            'additional_contact_name', 'additional_contact_title',
            'additional_contact_phone', 'additional_contact_email',
            # Notes
            'notes',
            # Workforce
            'hiring_status',
            'employee_count', 'jobs_added_expected',
            'jobs_added_last_year', 'jobs_lost_last_year',
            # Facility
            'building_size_sqft', 'at_capacity',
            # Expansion
            'expansion_adding_sq_footage', 'expansion_new_building',
            'expansion_adding_equipment', 'expansion_capex_planned',
            'expansion_notes',
            # Volunteer impact
            'volunteer_helped', 'volunteer_helped_notes',
            # Lead + follow-up
            'received_business_lead',
            'follow_up_needed', 'follow_up_notes',
        )
        widgets = {
            'contact_name': forms.TextInput(attrs={**_fc, 'placeholder': 'Name of person you spoke with'}),
            'additional_contact_name':  forms.TextInput(attrs={**_fc, 'placeholder': 'Name'}),
            'additional_contact_title': forms.TextInput(attrs={**_fc, 'placeholder': 'Title'}),
            'additional_contact_phone': forms.TextInput(attrs={**_fc, 'placeholder': 'Phone'}),
            'additional_contact_email': forms.EmailInput(attrs={**_fc, 'placeholder': 'Email'}),
            'notes': forms.Textarea(attrs={**_fc, 'rows': 5,
                'placeholder': 'What did you learn? What was the general tone of the conversation?'}),
            'hiring_status':       forms.Select(attrs=_fs),
            'employee_count':      forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 45', 'min': 0}),
            'jobs_added_expected': forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 10', 'min': 0}),
            'jobs_added_last_year': forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 5',  'min': 0}),
            'jobs_lost_last_year':  forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 2',  'min': 0}),
            'building_size_sqft': forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 12000', 'min': 0}),
            'at_capacity':        forms.Select(attrs=_fs),
            'expansion_adding_sq_footage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_new_building':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_adding_equipment':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_capex_planned':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_notes': forms.Textarea(attrs={**_fc, 'rows': 2,
                'placeholder': 'Additional expansion details (optional)'}),
            'volunteer_helped':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'volunteer_helped_notes': forms.Textarea(attrs={**_fc, 'rows': 3,
                'placeholder': 'Describe how you helped...'}),
            'received_business_lead': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_needed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_notes':  forms.Textarea(attrs={**_fc, 'rows': 3,
                'placeholder': 'Describe the follow-up needed (optional)'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hiring_status'].required = True
        self.fields['hiring_status'].empty_label = None

    labels = {
            'contact_name':            'Who did you speak with?',
            'additional_contact_name': 'Name',
            'notes':                   'Visit Notes',
            'hiring_status':           'Hiring / Layoff Status',
            'employee_count':          'Current Employees',
            'jobs_added_expected':     'Expected Jobs to be Added',
            'jobs_added_last_year':    'Jobs Added Last Year',
            'jobs_lost_last_year':     'Jobs Lost Last Year',
            'building_size_sqft':      'Current Building Size (sq ft)',
            'at_capacity':             'At Capacity?',
            'expansion_adding_sq_footage': 'Adding square footage',
            'expansion_new_building':      'Looking for / moving to a new building',
            'expansion_adding_equipment':  'Adding equipment',
            'expansion_capex_planned':     'Capital expenditure planned',
            'expansion_notes':             'Expansion details',
            'volunteer_helped':       'I assisted this company with a problem during this visit',
            'volunteer_helped_notes': 'How did you assist?',
            'received_business_lead': 'I received a business lead or referral from this visit',
            'follow_up_needed':       'Follow-up needed?',
            'follow_up_notes':        'Follow-up Details',
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

class CreateAdminForm(UserCreationForm):
    first_name   = forms.CharField(max_length=50, required=False,
                                   widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}))
    last_name    = forms.CharField(max_length=50, required=False,
                                   widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}))
    email        = forms.EmailField(required=True,
                                    widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}))
    is_superuser = forms.BooleanField(required=False, label='Grant superuser privileges',
                                      help_text='Superusers have full access including the Django admin panel.',
                                      widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model  = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('username', 'password1', 'password2'):
            self.fields[field_name].widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email        = self.cleaned_data['email']
        user.first_name   = self.cleaned_data['first_name']
        user.last_name    = self.cleaned_data['last_name']
        user.is_staff     = True
        user.is_superuser = self.cleaned_data['is_superuser']
        if commit:
            user.save()
        return user

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
