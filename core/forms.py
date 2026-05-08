from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Assignment, AssignmentRequest, Company, ContactAttempt, InviteCode, Notice, Resource, VisitNote, Message, Reply

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
            'contact_name',
            'additional_contact_name', 'additional_contact_title',
            'additional_contact_phone', 'additional_contact_email',
            'notes',
            'hiring_status',
            'employee_count', 'jobs_added_expected',
            'jobs_added_last_year', 'jobs_lost_last_year',
            'building_size_sqft', 'at_capacity',
            'expansion_adding_sq_footage', 'expansion_new_building',
            'expansion_adding_equipment', 'expansion_capex_planned',
            'expansion_notes',
            'volunteer_helped', 'volunteer_helped_notes',
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
            'hiring_status':        forms.Select(attrs=_fs),
            'employee_count':       forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 45',    'min': 0}),
            'jobs_added_expected':  forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 10',    'min': 0}),
            'jobs_added_last_year': forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 5',     'min': 0}),
            'jobs_lost_last_year':  forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 2',     'min': 0}),
            'building_size_sqft':   forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 12000', 'min': 0}),
            'at_capacity':          forms.Select(attrs=_fs),
            'expansion_adding_sq_footage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_new_building':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_adding_equipment':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_capex_planned':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_notes':        forms.Textarea(attrs={**_fc, 'rows': 2,
                'placeholder': 'Additional expansion details (optional)'}),
            'volunteer_helped':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'volunteer_helped_notes': forms.Textarea(attrs={**_fc, 'rows': 3,
                'placeholder': 'Describe how you assisted...'}),
            'received_business_lead': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_needed':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_notes':        forms.Textarea(attrs={**_fc, 'rows': 3,
                'placeholder': 'Describe the follow-up needed (optional)'}),
        }
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
            'volunteer_helped':            'I assisted this company with a problem during this visit',
            'volunteer_helped_notes':      'How did you assist?',
            'received_business_lead':      'I received a business lead or referral from this visit',
            'follow_up_needed':            'Follow-up needed?',
            'follow_up_notes':             'Follow-up Details',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Required on form but blank=True on model to allow existing rows without a value
        self.fields['hiring_status'].required = True


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
        fields = ('name', 'industry', 'address', 'city', 'state', 'zip_code', 'phone', 'email',
                  'primary_contact_name')
        widgets = {
            'name':                 forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company name'}),
            'industry':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Industry'}),
            'address':              forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
            'city':                 forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state':                forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'zip_code':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zip code'}),
            'phone':                forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone'}),
            'email':                forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'primary_contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact name'}),
        }


class _CompanyWithIndustryField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} — {obj.industry}" if obj.industry else obj.name


class QuickAssignForm(forms.Form):
    company = _CompanyWithIndustryField(
        queryset=Company.objects.filter(status=Company.STATUS_UNASSIGNED).order_by('industry', 'name'),
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


class NoticeForm(forms.ModelForm):
    class Meta:
        model  = Notice
        fields = ('title', 'body', 'link_url', 'link_text', 'is_active', 'expires_at')
        widgets = {
            'title':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Volunteer Appreciation Night — June 15'}),
            'body':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional details...'}),
            'link_url':   forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'link_text':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. RSVP here'}),
            'is_active':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
        labels = {
            'link_url':   'Button link (optional)',
            'link_text':  'Button label (optional)',
            'expires_at': 'Expires at',
        }


class VisitExportForm(forms.Form):
    date_from = forms.DateField(
        required=False,
        label='From',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
    )
    date_to = forms.DateField(
        required=False,
        label='To',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
    )
    industry = forms.ChoiceField(
        required=False,
        label='Industry',
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    volunteer = forms.ModelChoiceField(
        required=False,
        label='Volunteer',
        queryset=User.objects.filter(is_active=True, is_staff=False).order_by('first_name', 'last_name'),
        empty_label='All volunteers',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        industries = (
            Company.objects.exclude(industry='')
            .values_list('industry', flat=True)
            .distinct().order_by('industry')
        )
        self.fields['industry'].choices = [('', 'All industries')] + [(i, i) for i in industries]


class ResourceForm(forms.ModelForm):
    class Meta:
        model  = Resource
        fields = ['title', 'description', 'category', 'url', 'sort_order', 'is_active']
        widgets = {
            'title':       forms.TextInput(attrs=_fc),
            'description': forms.Textarea(attrs={**_fc, 'rows': 3}),
            'category':    forms.Select(attrs=_fs),
            'url':         forms.URLInput(attrs={**_fc, 'placeholder': 'https://'}),
            'sort_order':  forms.NumberInput(attrs=_fc),
        }
