import csv
import io

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path

from .forms import CompanyCSVUploadForm
from .models import Assignment, Badge, Company, ContactAttempt, InviteCode, Message, Reply, UserBadge, VisitNote

# ---------------------------------------------------------------------------
# Site branding
# ---------------------------------------------------------------------------
admin.site.site_header  = "EDAWN Administration"
admin.site.site_title   = "EDAWN Admin"
admin.site.index_title  = "Dashboard"


# ---------------------------------------------------------------------------
# Custom admin index context
# ---------------------------------------------------------------------------
_original_index = admin.AdminSite.index


def _custom_index(self, request, extra_context=None):
    extra_context = extra_context or {}
    extra_context.update({
        'total_companies':    Company.objects.count(),
        'unassigned_count':   Company.objects.filter(status=Company.STATUS_UNASSIGNED).count(),
        'active_assignments': Assignment.objects.filter(status=Assignment.STATUS_ACTIVE).count(),
        'total_visited':      Company.objects.filter(status=Company.STATUS_VISITED).count(),
        'total_volunteers':   User.objects.filter(is_active=True, is_staff=False).count(),
        'recent_assignments': (
            Assignment.objects.select_related('company', 'volunteer')
            .order_by('-assigned_date')[:8]
        ),
        'recent_companies':   Company.objects.order_by('-created_at')[:8],
    })
    return _original_index(self, request, extra_context=extra_context)


admin.AdminSite.index = _custom_index

# ---------------------------------------------------------------------------
# User (re-register with search_fields for autocomplete)
# ---------------------------------------------------------------------------
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    search_fields = ('username', 'first_name', 'last_name', 'email')


# ---------------------------------------------------------------------------
# Invite Codes
# ---------------------------------------------------------------------------

@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    list_display    = ('short_code', 'status_display', 'created_by', 'used_by', 'created_at')
    list_filter     = ('used_at',)
    readonly_fields = ('code', 'created_by', 'used_by', 'used_at')
    search_fields   = ('code', 'used_by__username', 'created_by__username')
    exclude         = ('created_by',)

    @admin.display(description='Code')
    def short_code(self, obj):
        return obj.code

    @admin.display(description='Status')
    def status_display(self, obj):
        if obj.used_by:
            return f"Used by {obj.used_by.username}"
        return "Available"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_urls(self):
        return [
            path('generate/', self.admin_site.admin_view(self.generate_invite_view),
                 name='generate-invite'),
        ] + super().get_urls()

    def generate_invite_view(self, request):
        """One-click invite generation with a copyable registration link."""
        invite = None
        register_url = None

        if request.method == 'POST':
            invite = InviteCode.objects.create(created_by=request.user)
            register_url = request.build_absolute_uri(
                f'/register/?invite={invite.code}'
            )

        # Show recent unused invites
        available = InviteCode.objects.filter(used_by__isnull=True).select_related('created_by')[:10]

        return render(request, 'admin/generate_invite.html', {
            'title':        'Generate Invite Link',
            'invite':       invite,
            'register_url': register_url,
            'available':    available,
            'opts':         self.model._meta,
        })


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------

class ContactAttemptInline(admin.TabularInline):
    model          = ContactAttempt
    extra          = 0
    readonly_fields = ('attempted_by', 'attempt_date', 'method', 'notes')
    can_delete     = False


class VisitNoteInline(admin.TabularInline):
    model           = VisitNote
    extra           = 0
    readonly_fields = ('visited_by', 'visit_date', 'notes', 'follow_up_needed', 'follow_up_notes')
    can_delete      = False


class AssignmentInline(admin.TabularInline):
    model               = Assignment
    extra               = 1
    autocomplete_fields = ('volunteer',)
    readonly_fields     = ('assigned_by', 'assigned_date', 'completed_date')
    fields              = ('volunteer', 'status', 'assigned_by', 'assigned_date', 'completed_date')
    show_change_link    = True


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display   = ('name', 'city', 'state', 'industry', 'status', 'primary_contact_name', 'phone')
    list_filter    = ('status', 'state', 'industry')
    search_fields  = ('name', 'city', 'industry', 'primary_contact_name', 'email', 'phone')
    list_editable  = ('status',)
    readonly_fields = ('created_at', 'updated_at')
    ordering       = ('name',)
    inlines        = [AssignmentInline]
    fieldsets = (
        ('Company Info', {
            'fields': ('name', 'industry', 'status', 'notes'),
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'zip_code'),
        }),
        ('Contact Info', {
            'fields': ('phone', 'email', 'website', 'primary_contact_name', 'primary_contact_title'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, Assignment) and not obj.assigned_by_id:
                obj.assigned_by = request.user
            obj.save()
            # Keep company status in sync
            if isinstance(obj, Assignment) and obj.status == Assignment.STATUS_ACTIVE:
                Company.objects.filter(pk=obj.company_id).update(status=Company.STATUS_ASSIGNED)
        formset.save_m2m()

    def get_urls(self):
        return [
            path('import-csv/', self.admin_site.admin_view(self.import_csv_view), name='company-import-csv'),
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['import_csv_url'] = 'import-csv/'
        return super().changelist_view(request, extra_context=extra_context)

    def import_csv_view(self, request):
        if request.method == 'POST':
            form = CompanyCSVUploadForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file  = request.FILES['csv_file']
                overwrite = form.cleaned_data.get('overwrite_existing', False)
                try:
                    decoded = csv_file.read().decode('utf-8-sig')
                    reader  = csv.DictReader(io.StringIO(decoded))

                    # Flexible column name mapping
                    FIELD_MAP = {
                        'name':                  'name',
                        'address':               'address',
                        'city':                  'city',
                        'state':                 'state',
                        'zip':                   'zip_code',
                        'zip_code':              'zip_code',
                        'phone':                 'phone',
                        'email':                 'email',
                        'website':               'website',
                        'industry':              'industry',
                        'contact_name':          'primary_contact_name',
                        'primary_contact_name':  'primary_contact_name',
                        'contact_title':         'primary_contact_title',
                        'primary_contact_title': 'primary_contact_title',
                        'notes':                 'notes',
                    }

                    created = updated = skipped = 0
                    row_errors = []

                    for i, row in enumerate(reader, start=2):
                        name = row.get('name', '').strip()
                        if not name:
                            row_errors.append(f"Row {i}: skipped (no name)")
                            skipped += 1
                            continue

                        data = {}
                        for csv_col, model_field in FIELD_MAP.items():
                            val = row.get(csv_col, '').strip()
                            if val:
                                data[model_field] = val

                        existing = Company.objects.filter(name__iexact=name).first()
                        if existing:
                            if overwrite:
                                for field, val in data.items():
                                    setattr(existing, field, val)
                                existing.save()
                                updated += 1
                            else:
                                skipped += 1
                        else:
                            data['name'] = name
                            Company.objects.create(**data)
                            created += 1

                    summary = f"Import complete: {created} created, {updated} updated, {skipped} skipped."
                    if row_errors:
                        summary += " Errors: " + "; ".join(row_errors[:5])
                    messages.success(request, summary)
                    return HttpResponseRedirect('../')

                except Exception as exc:
                    messages.error(request, f"Import failed: {exc}")
        else:
            form = CompanyCSVUploadForm()

        return render(request, 'admin/company_import_csv.html', {
            'form':  form,
            'title': 'Import Companies from CSV',
            'opts':  self.model._meta,
        })


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display   = ('company', 'volunteer', 'assigned_by', 'status', 'assigned_date',
                      'attempt_count', 'completed_date')
    list_filter    = ('status', 'assigned_date')
    search_fields  = ('company__name', 'volunteer__username', 'volunteer__first_name',
                      'volunteer__last_name')
    autocomplete_fields = ('company', 'volunteer', 'assigned_by')
    readonly_fields = ('assigned_date', 'completed_date')
    ordering       = ('-assigned_date',)
    inlines        = [ContactAttemptInline, VisitNoteInline]

    @admin.display(description='Attempts')
    def attempt_count(self, obj):
        return f"{obj.contact_attempts.count()}/3"

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.assigned_by_id:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)
        # Keep company status in sync
        if obj.status == Assignment.STATUS_ACTIVE:
            Company.objects.filter(pk=obj.company_id).update(status=Company.STATUS_ASSIGNED)


# ContactAttempt and VisitNote are managed via inlines on Assignment — not registered at top level.


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------

class UserBadgeInline(admin.TabularInline):
    model          = UserBadge
    extra          = 1
    autocomplete_fields = ('user',)
    readonly_fields = ('earned_at',)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display    = ('name', 'icon', 'criteria_type', 'criteria_value', 'times_awarded', 'sort_order')
    list_filter     = ('criteria_type',)
    list_editable   = ('sort_order',)
    search_fields   = ('name', 'description')
    ordering        = ('sort_order', 'name')
    inlines         = [UserBadgeInline]

    @admin.display(description='Awarded')
    def times_awarded(self, obj):
        return obj.awards.count()


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display      = ('user', 'badge', 'earned_at')
    list_filter       = ('badge', 'earned_at')
    search_fields     = ('user__username', 'user__first_name', 'user__last_name', 'badge__name')
    autocomplete_fields = ('user', 'badge')
    readonly_fields   = ('earned_at',)


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class ReplyInline(admin.TabularInline):
    model          = Reply
    extra          = 0
    readonly_fields = ('sender', 'created_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display    = ('subject', 'sender', 'is_private', 'reply_count', 'created_at')
    list_filter     = ('is_private', 'created_at')
    search_fields   = ('subject', 'body', 'sender__username', 'sender__first_name', 'sender__last_name')
    readonly_fields = ('created_at',)
    inlines         = [ReplyInline]

    @admin.display(description='Replies')
    def reply_count(self, obj):
        return obj.replies.count()
