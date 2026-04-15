import csv
import io

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path

from .forms import CompanyCSVUploadForm
from .models import Assignment, Company, ContactAttempt, Goal, VisitNote

# ---------------------------------------------------------------------------
# Site branding
# ---------------------------------------------------------------------------
admin.site.site_header  = "EDAWN Administration"
admin.site.site_title   = "EDAWN Admin"
admin.site.index_title  = "Site Administration"

# ---------------------------------------------------------------------------
# User (re-register with search_fields for autocomplete)
# ---------------------------------------------------------------------------
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    search_fields = ('username', 'first_name', 'last_name', 'email')


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
    model           = Assignment
    extra           = 0
    readonly_fields = ('volunteer', 'assigned_by', 'assigned_date', 'status', 'completed_date')
    can_delete      = False
    show_change_link = True


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


# ---------------------------------------------------------------------------
# ContactAttempt
# ---------------------------------------------------------------------------

@admin.register(ContactAttempt)
class ContactAttemptAdmin(admin.ModelAdmin):
    list_display  = ('assignment', 'attempted_by', 'method', 'attempt_date')
    list_filter   = ('method', 'attempt_date')
    search_fields = ('assignment__company__name', 'attempted_by__username', 'notes')
    readonly_fields = ('attempt_date',)


# ---------------------------------------------------------------------------
# VisitNote
# ---------------------------------------------------------------------------

@admin.register(VisitNote)
class VisitNoteAdmin(admin.ModelAdmin):
    list_display  = ('assignment', 'visited_by', 'visit_date', 'follow_up_needed')
    list_filter   = ('follow_up_needed', 'visit_date')
    search_fields = ('assignment__company__name', 'visited_by__username', 'notes')
    readonly_fields = ('visit_date',)


# ---------------------------------------------------------------------------
# Goal
# ---------------------------------------------------------------------------

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display  = ('title', 'user', 'current_value', 'target_value', 'progress_display', 'due_date')
    list_filter   = ('due_date',)
    search_fields = ('title', 'description', 'user__username')
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    ordering      = ('-created_at',)
    fieldsets = (
        (None,       {'fields': ('title', 'description', 'user')}),
        ('Progress', {'fields': ('current_value', 'target_value', 'due_date')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Progress')
    def progress_display(self, obj):
        return f"{obj.progress_percentage}% ({obj.current_value}/{obj.target_value})"
