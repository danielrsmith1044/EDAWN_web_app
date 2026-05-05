import csv
import io
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Max, Min, Q
from django.utils import timezone
from django.utils.html import format_html

from .models import Assignment, AssignmentRequest, Badge, Company, ContactAttempt, InviteCode, Message, Notice, Reply, Resource, UserBadge, UserProfile, VisitNote
from .forms import (RegisterForm, ContactAttemptForm, VisitNoteForm, CompanyContactUpdateForm,
                     MessageForm, ReplyForm, QuickCompanyForm, QuickAssignForm, CreateAdminForm,
                     CompanyCSVUploadForm, VisitExportForm, NoticeForm, ResourceForm)
from .ratelimit import ratelimit


def _get_assignment(pk, user):
    """Return assignment by pk; staff see any, volunteers only their own."""
    if user.is_staff:
        return get_object_or_404(Assignment, pk=pk)
    return get_object_or_404(Assignment, pk=pk, volunteer=user)


# ---------------------------------------------------------------------------
# Landing page (public)
# ---------------------------------------------------------------------------

def landing(request):
    return render(request, 'core/landing.html')


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@ratelimit(max_attempts=5, window=300, key_prefix='register')
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account was created.')
            return redirect('dashboard')
    else:
        initial = {}
        if request.GET.get('invite'):
            initial['invite_code'] = request.GET['invite']
        form = RegisterForm(initial=initial)
    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    # GET requests show a confirmation, but the sidebar form POSTs directly
    return redirect('dashboard')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _leaderboard_qs():
    return (
        User.objects
        .select_related('profile')
        .annotate(completed_count=Count(
            'assignments',
            filter=Q(assignments__status=Assignment.STATUS_COMPLETED)
        ))
        .filter(completed_count__gt=0)
        .order_by('-completed_count')
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    user = request.user
    active_assignments = (
        Assignment.objects
        .filter(volunteer=user, status=Assignment.STATUS_ACTIVE)
        .select_related('company')
        .order_by('company__name')
    )
    # Recent messages: group messages + user's own private messages (staff see all)
    if user.is_staff:
        recent_messages = Message.objects.all()[:5]
    else:
        recent_messages = Message.objects.filter(
            Q(is_private=False) | Q(sender=user)
        )[:5]

    my_badges = (
        UserBadge.objects
        .filter(user=user)
        .select_related('badge')
        .order_by('-earned_at')
    )

    context = {
        'active_assignments': active_assignments,
        'my_badges':       my_badges[:6],
        'badge_count':     my_badges.count(),
        'total_badges':    Badge.objects.count(),
        'top_users':       _leaderboard_qs()[:5],
        'recent_messages': recent_messages,
        'total_assigned':  Assignment.objects.filter(volunteer=user).count(),
        'completed_count': Assignment.objects.filter(volunteer=user, status=Assignment.STATUS_COMPLETED).count(),
        'lost_count':      Assignment.objects.filter(volunteer=user, status=Assignment.STATUS_LOST).count(),
        'open_count':      active_assignments.count(),
    }

    if user.is_staff:
        context['unassigned_count'] = Company.objects.filter(status=Company.STATUS_UNASSIGNED).count()

    profile = getattr(user, 'profile', None)
    if profile and not profile.training_completed and settings.TRAINING_CALENDAR_URL:
        context['training_calendar_url'] = settings.TRAINING_CALENDAR_URL

    context['notices'] = Notice.objects.filter(is_active=True, expires_at__gt=timezone.now())

    return render(request, 'core/dashboard.html', context)


# ---------------------------------------------------------------------------
# Admin Quick Actions (staff only)
# ---------------------------------------------------------------------------

@staff_member_required
def quick_add_company(request):
    if request.method == 'POST':
        form = QuickCompanyForm(request.POST)
        if form.is_valid():
            company = form.save()
            messages.success(request, f'Company "{company.name}" added.')
            return redirect('quick_add_company')
    else:
        form = QuickCompanyForm()
    recent = Company.objects.order_by('-created_at')[:5]
    return render(request, 'core/admin_add_company.html', {'form': form, 'recent': recent})


@staff_member_required
def quick_assign(request):
    if request.method == 'POST':
        form = QuickAssignForm(request.POST)
        if form.is_valid():
            company   = form.cleaned_data['company']
            volunteer = form.cleaned_data['volunteer']

            profile, _ = UserProfile.objects.get_or_create(user=volunteer)
            if not profile.bbv_certified:
                active_count = Assignment.objects.filter(
                    volunteer=volunteer, status=Assignment.STATUS_ACTIVE
                ).count()
                if active_count >= 1:
                    vol_name = volunteer.get_full_name() or volunteer.username
                    messages.error(
                        request,
                        f"{vol_name} already has an active assignment. "
                        f"Volunteers are limited to 1 active company until they earn "
                        f"BBV certification."
                    )
                    return redirect('staff_assign')

            Assignment.objects.create(
                company=company,
                volunteer=volunteer,
                assigned_by=request.user,
            )
            company.status = Company.STATUS_ASSIGNED
            company.save(update_fields=['status'])
            vol_name = volunteer.get_full_name() or volunteer.username
            messages.success(request, f'"{company.name}" assigned to {vol_name}.')
            return redirect('staff_assign')
    else:
        initial = {}
        company_pk = request.GET.get('company')
        if company_pk and company_pk.isdigit():
            initial['company'] = company_pk
        form = QuickAssignForm(initial=initial)
    recent = Assignment.objects.select_related('company', 'volunteer').order_by('-assigned_date')[:5]
    return render(request, 'core/admin_assign.html', {'form': form, 'recent': recent})


@staff_member_required
def create_admin(request):
    if request.method == 'POST':
        form = CreateAdminForm(request.POST)
        if form.is_valid():
            user = form.save()
            label = user.get_full_name() or user.username
            role  = 'Superuser' if user.is_superuser else 'Admin'
            messages.success(request, f'{role} account created for {label}.')
            return redirect('create_admin')
    else:
        form = CreateAdminForm()
    admins = list(User.objects.filter(is_staff=True).order_by('username'))
    return render(request, 'core/admin_create_admin.html', {'form': form, 'admins': admins})


@staff_member_required
def quick_invite(request):
    invite_link = None
    if request.method == 'POST':
        invite = InviteCode.objects.create(created_by=request.user)
        invite_link = request.build_absolute_uri(f'/register/?invite={invite.code}')
    available = InviteCode.objects.filter(used_by__isnull=True).select_related('created_by')[:10]
    return render(request, 'core/admin_invite.html', {
        'invite_link':          invite_link,
        'available':            available,
        'training_calendar_url': settings.TRAINING_CALENDAR_URL,
    })


# ---------------------------------------------------------------------------
# Companies / Assignments
# ---------------------------------------------------------------------------

@login_required
def company_list(request):
    status_filter    = request.GET.get('status', 'active')
    industry_filter  = request.GET.get('industry', '')
    volunteer_filter = request.GET.get('volunteer', '') if request.user.is_staff else ''

    if request.user.is_staff:
        base_qs = (Assignment.objects.all()
                   .select_related('company', 'volunteer')
                   .prefetch_related('contact_attempts'))
    else:
        base_qs = (Assignment.objects.filter(volunteer=request.user)
                   .select_related('company')
                   .prefetch_related('contact_attempts'))

    # Filter out unassigned-only view before applying status filter
    if status_filter == 'unassigned':
        assignments = Assignment.objects.none()
    else:
        assignments = base_qs
        if status_filter == 'active':
            assignments = assignments.filter(status=Assignment.STATUS_ACTIVE)
        elif status_filter == 'completed':
            assignments = assignments.filter(status=Assignment.STATUS_COMPLETED)
        elif status_filter == 'lost':
            assignments = assignments.filter(status=Assignment.STATUS_LOST)

    if industry_filter:
        assignments = assignments.filter(company__industry=industry_filter)

    if volunteer_filter:
        assignments = assignments.filter(volunteer__id=volunteer_filter)

    # Unassigned companies — staff only, shown for 'all' and 'unassigned' filters
    unassigned_companies = None
    if request.user.is_staff and status_filter in ('all', 'unassigned'):
        uq = Company.objects.filter(status=Company.STATUS_UNASSIGNED)
        if industry_filter:
            uq = uq.filter(industry=industry_filter)
        unassigned_companies = uq.order_by('name')

    # Industry options
    if request.user.is_staff:
        industries = (
            Company.objects.exclude(industry='')
            .values_list('industry', flat=True)
            .distinct().order_by('industry')
        )
        volunteers = User.objects.filter(is_active=True, is_staff=False).order_by('first_name', 'last_name')
    else:
        industries = (
            Assignment.objects.filter(volunteer=request.user)
            .exclude(company__industry='')
            .values_list('company__industry', flat=True)
            .distinct().order_by('company__industry')
        )
        volunteers = None

    context = {
        'assignments':          assignments.order_by('company__name'),
        'unassigned_companies': unassigned_companies,
        'status_filter':        status_filter,
        'industry_filter':      industry_filter,
        'volunteer_filter':     volunteer_filter,
        'industries':           industries,
        'volunteers':           volunteers,
    }
    return render(request, 'core/company_list.html', context)


@login_required
def company_detail(request, pk):
    assignment       = _get_assignment(pk, request.user)
    contact_attempts = list(assignment.contact_attempts.all())
    visit_notes      = assignment.visit_notes.all()

    context = {
        'assignment':         assignment,
        'company':            assignment.company,
        'contact_attempts':   contact_attempts,
        'visit_notes':        visit_notes,
        'contact_form':       ContactAttemptForm(),
        'attempts_remaining': max(0, 3 - len(contact_attempts)),
        'contact_attempts_count': len(contact_attempts),
        'is_owner':           request.user == assignment.volunteer,
    }
    return render(request, 'core/company_detail.html', context)


@login_required
def log_contact_attempt(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, volunteer=request.user)

    if not assignment.is_active:
        messages.error(request, "This assignment is no longer active.")
        return redirect('company_detail', pk=pk)

    if request.method == 'POST':
        form = ContactAttemptForm(request.POST)
        if form.is_valid():
            attempt              = form.save(commit=False)
            attempt.assignment   = assignment
            attempt.attempted_by = request.user
            attempt.save()

            assignment.refresh_from_db()
            count = assignment.contact_attempts.count()
            if assignment.status == Assignment.STATUS_LOST:
                messages.warning(
                    request,
                    f"3 contact attempts reached — {assignment.company.name} has been marked as Lost."
                )
            else:
                messages.success(request, f"Contact attempt logged ({count}/3).")

    return redirect('company_detail', pk=pk)


@login_required
def log_visit(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, volunteer=request.user)
    company    = assignment.company

    if not assignment.is_active:
        messages.error(request, "This assignment is no longer active.")
        return redirect('company_detail', pk=pk)

    if request.method == 'POST':
        form         = VisitNoteForm(request.POST)
        contact_form = CompanyContactUpdateForm(request.POST, instance=company, prefix='contact')
        if form.is_valid() and contact_form.is_valid():
            contact_form.save()
            note            = form.save(commit=False)
            note.assignment = assignment
            note.visited_by = request.user
            note.save()
            messages.success(request, f"Visit to {company.name} recorded!")
            return redirect('company_detail', pk=pk)
    else:
        form         = VisitNoteForm()
        contact_form = CompanyContactUpdateForm(instance=company, prefix='contact')

    return render(request, 'core/log_visit.html', {
        'assignment':   assignment,
        'company':      company,
        'form':         form,
        'contact_form': contact_form,
    })


@login_required
def edit_visit_note(request, pk, note_pk):
    assignment = _get_assignment(pk, request.user)

    note = get_object_or_404(VisitNote, pk=note_pk, assignment=assignment)

    if not request.user.is_staff and note.visited_by != request.user:
        messages.error(request, "You can only edit your own visit notes.")
        return redirect('company_detail', pk=pk)

    company = assignment.company

    if request.method == 'POST':
        form         = VisitNoteForm(request.POST, instance=note)
        contact_form = CompanyContactUpdateForm(request.POST, instance=company, prefix='contact')
        if form.is_valid() and contact_form.is_valid():
            contact_form.save()
            form.save()
            messages.success(request, "Visit note updated.")
            return redirect('company_detail', pk=pk)
    else:
        form         = VisitNoteForm(instance=note)
        contact_form = CompanyContactUpdateForm(instance=company, prefix='contact')

    return render(request, 'core/log_visit.html', {
        'assignment':   assignment,
        'company':      company,
        'form':         form,
        'contact_form': contact_form,
        'editing':      True,
        'note':         note,
    })


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------

@login_required
def badge_list(request):
    all_badges = Badge.objects.all()
    earned_map = {
        ub.badge_id: ub.earned_at
        for ub in UserBadge.objects.filter(user=request.user)
    }
    badges = []
    for badge in all_badges:
        badges.append({
            'badge': badge,
            'earned': badge.pk in earned_map,
            'earned_at': earned_map.get(badge.pk),
        })
    context = {
        'badges': badges,
        'earned_count': len(earned_map),
        'total_count': len(all_badges),
    }
    return render(request, 'core/badge_list.html', context)


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

@login_required
def leaderboard(request):
    return render(request, 'core/leaderboard.html', {'users': _leaderboard_qs()})


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

@login_required
def message_list(request):
    filter_type = request.GET.get('filter', 'group')
    user = request.user

    if filter_type == 'private':
        if user.is_staff:
            qs = Message.objects.filter(is_private=True)
        else:
            qs = Message.objects.filter(
                Q(is_private=True, sender=user) | Q(recipient=user)
            )
    else:
        qs = Message.objects.filter(is_private=False, recipient__isnull=True)

    context = {
        'messages_list': qs.select_related('sender', 'recipient'),
        'filter_type':   filter_type,
    }
    return render(request, 'core/message_list.html', context)


@login_required
def message_detail(request, pk):
    message = get_object_or_404(Message, pk=pk)

    # Access control: private messages visible to sender, recipient, and staff
    if (message.is_private
            and not request.user.is_staff
            and message.sender != request.user
            and message.recipient != request.user):
        messages.error(request, "You don't have access to this message.")
        return redirect('message_list')

    if request.method == 'POST':
        form = ReplyForm(request.POST)
        if form.is_valid():
            reply         = form.save(commit=False)
            reply.message = message
            reply.sender  = request.user
            reply.save()
            messages.success(request, 'Reply posted.')
            return redirect('message_detail', pk=pk)
    else:
        form = ReplyForm()

    context = {
        'message': message,
        'replies': message.replies.select_related('sender'),
        'form':    form,
    }
    return render(request, 'core/message_detail.html', context)


@login_required
@ratelimit(max_attempts=10, window=300, key_prefix='msg_create')
def message_create(request):
    industries = (
        Company.objects.exclude(industry='')
        .values_list('industry', flat=True)
        .distinct().order_by('industry')
    )
    volunteers = User.objects.filter(is_active=True, is_staff=False).order_by('first_name', 'last_name')

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            body    = form.cleaned_data['body']

            if request.user.is_staff:
                group = request.POST.get('recipient_group', 'board')
                if group == 'all_volunteers':
                    recipients = list(User.objects.filter(is_active=True, is_staff=False))
                elif group == 'by_industry':
                    industry = request.POST.get('recipient_industry', '')
                    recipients = list(
                        User.objects.filter(
                            is_active=True, is_staff=False,
                            assignments__company__industry=industry,
                            assignments__status=Assignment.STATUS_ACTIVE,
                        ).distinct()
                    )
                elif group == 'specific_volunteer':
                    vol_pk = request.POST.get('recipient_user', '')
                    recipients = list(User.objects.filter(pk=vol_pk, is_active=True, is_staff=False))
                else:
                    recipients = None

                if recipients is not None:
                    for vol in recipients:
                        Message.objects.create(
                            sender=request.user, recipient=vol,
                            subject=subject, body=body, is_private=True,
                        )
                    count = len(recipients)
                    messages.success(request, f'Message sent to {count} volunteer{"s" if count != 1 else ""}.')
                    return redirect('message_list')

            msg        = form.save(commit=False)
            msg.sender = request.user
            msg.save()
            if msg.is_private:
                messages.success(request, 'Private message sent to admin.')
            else:
                messages.success(request, 'Message posted to the group.')
            return redirect('message_detail', pk=msg.pk)
    else:
        form = MessageForm()

    return render(request, 'core/message_create.html', {
        'form':       form,
        'industries': industries,
        'volunteers': volunteers,
    })


# ---------------------------------------------------------------------------
# Staff Portal
# ---------------------------------------------------------------------------

def _bbv_overdue_count(cutoff_90):
    return (
        User.objects
        .filter(is_active=True, is_staff=False, profile__bbv_certified=False)
        .annotate(
            first_assignment=Min('assignments__assigned_date'),
            completed_count=Count(
                'assignments',
                filter=Q(assignments__status=Assignment.STATUS_COMPLETED),
                distinct=True,
            ),
        )
        .filter(first_assignment__lt=cutoff_90, completed_count__gt=0)
        .count()
    )


_CSV_FIELD_MAP = {
    'name': 'name', 'address': 'address', 'city': 'city', 'state': 'state',
    'zip': 'zip_code', 'zip_code': 'zip_code', 'phone': 'phone',
    'email': 'email', 'website': 'website', 'industry': 'industry',
    'contact_name': 'primary_contact_name',
    'primary_contact_name': 'primary_contact_name',
    'contact_title': 'primary_contact_title',
    'primary_contact_title': 'primary_contact_title',
    'notes': 'notes',
}


@staff_member_required
def staff_dashboard(request):
    cutoff_60 = timezone.now() - timedelta(days=60)
    cutoff_45 = timezone.now() - timedelta(days=45)
    cutoff_90 = timezone.now() - timedelta(days=90)

    not_visited_60d = (
        Assignment.objects
        .filter(status=Assignment.STATUS_ACTIVE)
        .annotate(last_visit=Max('visit_notes__visit_date'))
        .filter(Q(last_visit__lt=cutoff_60) | Q(last_visit__isnull=True))
        .count()
    )

    overdue_volunteers = list(
        User.objects
        .filter(is_active=True, is_staff=False, assignments__status=Assignment.STATUS_ACTIVE)
        .annotate(
            last_visit=Max('assignments__visit_notes__visit_date'),
            oldest_active=Min('assignments__assigned_date',
                              filter=Q(assignments__status=Assignment.STATUS_ACTIVE)),
        )
        # oldest_active guard gives newly-assigned volunteers a 45-day grace period
        .filter(
            Q(last_visit__lt=cutoff_45) | Q(last_visit__isnull=True),
            oldest_active__lt=cutoff_45,
        )
        .distinct()
        .order_by('first_name', 'last_name')[:8]
    )

    context = {
        'total_companies':    Company.objects.count(),
        'unassigned_count':   Company.objects.filter(status=Company.STATUS_UNASSIGNED).count(),
        'active_count':       Assignment.objects.filter(status=Assignment.STATUS_ACTIVE).count(),
        'visited_count':      Company.objects.filter(status=Company.STATUS_VISITED).count(),
        'total_volunteers':   User.objects.filter(is_active=True, is_staff=False).count(),
        'not_visited_60d':    not_visited_60d,
        'overdue_count':      len(overdue_volunteers),
        'overdue_volunteers': overdue_volunteers,
        'bbv_overdue_count':    _bbv_overdue_count(cutoff_90),
        'pending_requests_count': AssignmentRequest.objects.filter(status=AssignmentRequest.STATUS_PENDING).count(),
        'recent_assignments': (
            Assignment.objects
            .select_related('company', 'volunteer')
            .order_by('-assigned_date')[:10]
        ),
    }
    return render(request, 'core/staff_dashboard.html', context)


@staff_member_required
def staff_volunteers(request):
    status_filter = request.GET.get('status', 'all')
    cutoff_45 = timezone.now() - timedelta(days=45)
    cutoff_90 = timezone.now() - timedelta(days=90)

    volunteers = (
        User.objects
        .filter(is_active=True, is_staff=False)
        .select_related('profile')
        .annotate(
            last_visit=Max('assignments__visit_notes__visit_date'),
            first_assignment=Min('assignments__assigned_date'),
            oldest_active=Min('assignments__assigned_date',
                              filter=Q(assignments__status=Assignment.STATUS_ACTIVE)),
            active_count=Count(
                'assignments',
                filter=Q(assignments__status=Assignment.STATUS_ACTIVE),
                distinct=True,
            ),
            completed_count=Count(
                'assignments',
                filter=Q(assignments__status=Assignment.STATUS_COMPLETED),
                distinct=True,
            ),
            lost_count=Count(
                'assignments',
                filter=Q(assignments__status=Assignment.STATUS_LOST),
                distinct=True,
            ),
        )
        .order_by('first_name', 'last_name', 'username')
    )

    if status_filter == 'overdue':
        volunteers = volunteers.filter(
            active_count__gt=0,
            oldest_active__lt=cutoff_45,
        ).filter(Q(last_visit__lt=cutoff_45) | Q(last_visit__isnull=True))
    elif status_filter == 'active':
        volunteers = volunteers.filter(active_count__gt=0)
    elif status_filter == 'unassigned':
        volunteers = volunteers.filter(active_count=0, completed_count=0, lost_count=0)
    elif status_filter == 'bbv_overdue':
        volunteers = volunteers.filter(
            profile__bbv_certified=False,
            first_assignment__lt=cutoff_90,
            completed_count__gt=0,
        )

    volunteers = list(volunteers)
    for vol in volunteers:
        vol.is_overdue = (
            bool(vol.active_count)
            and vol.oldest_active is not None
            and vol.oldest_active < cutoff_45
            and (vol.last_visit is None or vol.last_visit < cutoff_45)
        )

    context = {
        'volunteers':        volunteers,
        'status_filter':     status_filter,
        'cutoff_45':         cutoff_45,
        'cutoff_90':         cutoff_90,
        'total_count':       User.objects.filter(is_active=True, is_staff=False).count(),
        'bbv_overdue_count': _bbv_overdue_count(cutoff_90),
    }
    return render(request, 'core/staff_volunteers.html', context)


@staff_member_required
def staff_import_csv(request):
    if request.method == 'POST':
        form = CompanyCSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            overwrite = form.cleaned_data.get('overwrite_existing', False)
            try:
                decoded = request.FILES['csv_file'].read().decode('utf-8-sig')
                reader  = csv.DictReader(io.StringIO(decoded))
                created = updated = skipped = 0
                row_errors = []

                for i, row in enumerate(reader, start=2):
                    name = row.get('name', '').strip()
                    if not name:
                        row_errors.append(f"Row {i}: skipped (no name)")
                        skipped += 1
                        continue
                    data = {
                        model_field: row.get(csv_col, '').strip()
                        for csv_col, model_field in _CSV_FIELD_MAP.items()
                        if row.get(csv_col, '').strip()
                    }
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
                    summary += "  Errors: " + "; ".join(row_errors[:5])
                messages.success(request, summary)
                return redirect('staff_import_csv')
            except Exception as exc:
                messages.error(request, f"Import failed: {exc}")
    else:
        form = CompanyCSVUploadForm()

    recent = Company.objects.order_by('-created_at')[:10]
    return render(request, 'core/staff_import.html', {'form': form, 'recent': recent})


@staff_member_required
def staff_expansion_signals(request):
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    industry  = request.GET.get('industry', '')

    qs = (
        VisitNote.objects
        .filter(
            Q(expansion_adding_sq_footage=True) |
            Q(expansion_new_building=True) |
            Q(expansion_adding_equipment=True) |
            Q(expansion_capex_planned=True)
        )
        .select_related('assignment__company', 'visited_by')
        .order_by('-visit_date')
    )

    if date_from:
        qs = qs.filter(visit_date__date__gte=date_from)
    if date_to:
        qs = qs.filter(visit_date__date__lte=date_to)
    if industry:
        qs = qs.filter(assignment__company__industry=industry)

    industries = (
        Company.objects.exclude(industry='')
        .values_list('industry', flat=True)
        .distinct().order_by('industry')
    )

    context = {
        'signals':    qs,
        'count':      qs.count(),
        'date_from':  date_from,
        'date_to':    date_to,
        'industry':   industry,
        'industries': industries,
    }
    return render(request, 'core/staff_expansion_signals.html', context)


@staff_member_required
def staff_mark_training(request, pk):
    if request.method != 'POST':
        return redirect('staff_volunteers')
    volunteer = get_object_or_404(User, pk=pk, is_staff=False)
    profile, _ = UserProfile.objects.get_or_create(user=volunteer)
    name = volunteer.get_full_name() or volunteer.username
    if profile.training_completed:
        profile.training_completed      = False
        profile.training_completed_date = None
        messages.success(request, f"Training marked incomplete for {name}.")
    else:
        profile.training_completed      = True
        profile.training_completed_date = timezone.now().date()
        messages.success(request, f"Training marked complete for {name}.")
    profile.save(update_fields=['training_completed', 'training_completed_date'])
    return redirect('staff_volunteers')


@staff_member_required
def staff_mark_bbv(request, pk):
    if request.method != 'POST':
        return redirect('staff_volunteers')
    volunteer = get_object_or_404(User, pk=pk, is_staff=False)
    profile, _ = UserProfile.objects.get_or_create(user=volunteer)
    name = volunteer.get_full_name() or volunteer.username
    if profile.bbv_certified:
        profile.bbv_certified      = False
        profile.bbv_certified_date = None
        messages.success(request, f"BBV certification removed for {name}.")
    else:
        profile.bbv_certified      = True
        profile.bbv_certified_date = timezone.now()
        # Also award the badge if not already earned
        from .models import Badge, UserBadge
        bbv_badge = Badge.objects.filter(name='Certified Business Builder Volunteer').first()
        if bbv_badge:
            UserBadge.objects.get_or_create(user=volunteer, badge=bbv_badge)
        messages.success(request, f"BBV certification granted to {name}.")
    profile.save(update_fields=['bbv_certified', 'bbv_certified_date'])
    return redirect('staff_volunteers')


@staff_member_required
def staff_set_temp_password(request, pk):
    if request.method != 'POST':
        return redirect('staff_volunteers')
    volunteer = get_object_or_404(User, pk=pk, is_staff=False)
    alphabet = string.ascii_letters + string.digits
    temp_pw = ''.join(secrets.choice(alphabet) for _ in range(10))
    volunteer.set_password(temp_pw)
    volunteer.save(update_fields=['password'])
    name = volunteer.get_full_name() or volunteer.username
    messages.success(request, format_html(
        'Temporary password for {}: <strong class="font-monospace fs-5 ms-1">{}</strong>'
        ' — share this with them and ask them to change it after signing in.',
        name, temp_pw,
    ))
    return redirect('staff_volunteers')


# ---------------------------------------------------------------------------
# Resource library
# ---------------------------------------------------------------------------

@login_required
def resource_list(request):
    qs = Resource.objects.all() if request.user.is_staff else Resource.objects.filter(is_active=True)
    grouped = {}
    for res in qs:
        label = res.get_category_display()
        grouped.setdefault(label, []).append(res)
    return render(request, 'core/resource_list.html', {'grouped': grouped})


@staff_member_required
def resource_form(request, pk=None):
    resource = get_object_or_404(Resource, pk=pk) if pk else None
    if request.method == 'POST':
        form = ResourceForm(request.POST, instance=resource)
        if form.is_valid():
            form.save()
            messages.success(request, 'Resource saved.')
            return redirect('resource_list')
    else:
        form = ResourceForm(instance=resource)
    action_label = 'Edit Resource' if resource else 'Add Resource'
    return render(request, 'core/resource_form.html', {'form': form, 'resource': resource, 'action_label': action_label})


@staff_member_required
def resource_delete(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    if request.method == 'POST':
        resource.delete()
        messages.success(request, 'Resource deleted.')
    return redirect('resource_list')


# ---------------------------------------------------------------------------
# Visit data export
# ---------------------------------------------------------------------------

@staff_member_required
def staff_export_visits(request):
    form = VisitExportForm(request.GET or None)
    if request.GET and form.is_valid():
        qs = (
            VisitNote.objects
            .select_related('assignment__company', 'visited_by')
            .order_by('-visit_date')
        )
        if form.cleaned_data['date_from']:
            qs = qs.filter(visit_date__date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data['date_to']:
            qs = qs.filter(visit_date__date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data['industry']:
            qs = qs.filter(assignment__company__industry=form.cleaned_data['industry'])
        if form.cleaned_data['volunteer']:
            qs = qs.filter(visited_by=form.cleaned_data['volunteer'])

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="visit_export.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Visit Date', 'Company', 'Industry', 'City', 'State',
            'Volunteer', 'Contact Spoken To',
            'Employee Count', 'Hiring Status',
            'Jobs Added Last Year', 'Jobs Lost Last Year', 'Jobs Expected to Add',
            'Building Sq Ft', 'At Capacity',
            'Adding Sq Footage', 'New Building', 'Adding Equipment', 'CapEx Planned',
            'Expansion Notes',
            'Volunteer Helped', 'Volunteer Help Notes',
            'Business Lead Received',
            'Follow-up Needed', 'Follow-up Notes',
            'Visit Notes',
        ])
        for note in qs:
            company = note.assignment.company
            writer.writerow([
                note.visit_date.strftime('%Y-%m-%d'),
                company.name,
                company.industry,
                company.city,
                company.state,
                note.visited_by.get_full_name() or note.visited_by.username,
                note.contact_name,
                note.employee_count or '',
                note.get_hiring_status_display() if note.hiring_status else '',
                note.jobs_added_last_year or '',
                note.jobs_lost_last_year or '',
                note.jobs_added_expected or '',
                note.building_size_sqft or '',
                note.get_at_capacity_display() if note.at_capacity else '',
                'Yes' if note.expansion_adding_sq_footage else '',
                'Yes' if note.expansion_new_building else '',
                'Yes' if note.expansion_adding_equipment else '',
                'Yes' if note.expansion_capex_planned else '',
                note.expansion_notes,
                'Yes' if note.volunteer_helped else '',
                note.volunteer_helped_notes,
                'Yes' if note.received_business_lead else '',
                'Yes' if note.follow_up_needed else '',
                note.follow_up_notes,
                note.notes,
            ])
        return response

    columns = [
        'Visit Date', 'Company', 'Industry', 'City', 'State',
        'Volunteer', 'Contact Spoken To',
        'Employee Count', 'Hiring Status',
        'Jobs Added Last Year', 'Jobs Lost Last Year', 'Jobs Expected to Add',
        'Building Sq Ft', 'At Capacity',
        'Adding Sq Footage', 'New Building', 'Adding Equipment', 'CapEx Planned',
        'Expansion Notes',
        'Volunteer Helped', 'Volunteer Help Notes',
        'Business Lead Received',
        'Follow-up Needed', 'Follow-up Notes',
        'Visit Notes',
    ]
    return render(request, 'core/staff_export.html', {'form': form, 'columns': columns})


# ---------------------------------------------------------------------------
# Company browse & assignment requests
# ---------------------------------------------------------------------------

# Cap enforced at both request time and approval time to prevent race conditions
REQUEST_LIMIT = 3

@login_required
def company_browse(request):
    companies = (
        Company.objects.filter(status=Company.STATUS_UNASSIGNED)
        .annotate(pending_requests=Count(
            'assignment_requests',
            filter=Q(assignment_requests__status=AssignmentRequest.STATUS_PENDING),
        ))
        .order_by('industry', 'name')
    )

    # Filter by industry
    industry_filter = request.GET.get('industry', '')
    if industry_filter:
        companies = companies.filter(industry=industry_filter)

    industries = (
        Company.objects.filter(status=Company.STATUS_UNASSIGNED)
        .exclude(industry='').values_list('industry', flat=True)
        .distinct().order_by('industry')
    )

    # Current user's pending requests
    my_requests = AssignmentRequest.objects.filter(
        volunteer=request.user, status=AssignmentRequest.STATUS_PENDING
    ).values_list('company_id', flat=True)

    profile = getattr(request.user, 'profile', None)
    at_cap = (
        not getattr(profile, 'bbv_certified', False)
        and Assignment.objects.filter(volunteer=request.user, status=Assignment.STATUS_ACTIVE).exists()
    )

    context = {
        'companies':       companies,
        'industries':      industries,
        'industry_filter': industry_filter,
        'my_request_ids':  set(my_requests),
        'pending_count':   len(my_requests),
        'request_limit':   REQUEST_LIMIT,
        'at_cap':          at_cap,
    }
    return render(request, 'core/company_browse.html', context)


@login_required
def toggle_assignment_request(request, pk):
    if request.method != 'POST':
        return redirect('company_browse')

    company = get_object_or_404(Company, pk=pk, status=Company.STATUS_UNASSIGNED)
    existing = AssignmentRequest.objects.filter(
        volunteer=request.user, company=company
    ).first()

    if existing and existing.status == AssignmentRequest.STATUS_PENDING:
        existing.delete()
        messages.success(request, f'Request for "{company.name}" cancelled.')
        return redirect('company_browse')

    # Check cap
    pending_count = AssignmentRequest.objects.filter(
        volunteer=request.user, status=AssignmentRequest.STATUS_PENDING
    ).count()
    if pending_count >= REQUEST_LIMIT:
        messages.error(request, f'You can have at most {REQUEST_LIMIT} pending requests at a time.')
        return redirect('company_browse')

    # Check BBV cap
    profile = getattr(request.user, 'profile', None)
    if not getattr(profile, 'bbv_certified', False):
        if Assignment.objects.filter(volunteer=request.user, status=Assignment.STATUS_ACTIVE).exists():
            messages.error(request, 'You already have an active assignment. Complete it before requesting another company.')
            return redirect('company_browse')

    AssignmentRequest.objects.create(volunteer=request.user, company=company)
    messages.success(request, f'Request submitted for "{company.name}".')
    return redirect('company_browse')


# ---------------------------------------------------------------------------
# Staff — manage requests
# ---------------------------------------------------------------------------

@staff_member_required
def staff_requests(request):
    pending = (
        AssignmentRequest.objects
        .filter(status=AssignmentRequest.STATUS_PENDING)
        .select_related('volunteer', 'company')
        .order_by('company__name', 'created_at')
    )
    recent_actioned = (
        AssignmentRequest.objects
        .exclude(status=AssignmentRequest.STATUS_PENDING)
        .select_related('volunteer', 'company')
        .order_by('-created_at')[:20]
    )
    return render(request, 'core/staff_requests.html', {
        'pending':        pending,
        'recent_actioned': recent_actioned,
    })


@staff_member_required
def staff_approve_request(request, pk):
    if request.method != 'POST':
        return redirect('staff_requests')
    req = get_object_or_404(AssignmentRequest, pk=pk, status=AssignmentRequest.STATUS_PENDING)

    # Enforce BBV cap
    profile, _ = UserProfile.objects.get_or_create(user=req.volunteer)
    if not profile.bbv_certified:
        active_count = Assignment.objects.filter(
            volunteer=req.volunteer, status=Assignment.STATUS_ACTIVE
        ).count()
        if active_count >= 1:
            vol_name = req.volunteer.get_full_name() or req.volunteer.username
            messages.error(request, f'{vol_name} already has an active assignment and is not BBV certified.')
            return redirect('staff_requests')

    Assignment.objects.create(
        company=req.company,
        volunteer=req.volunteer,
        assigned_by=request.user,
    )
    req.company.status = Company.STATUS_ASSIGNED
    req.company.save(update_fields=['status'])

    req.status = AssignmentRequest.STATUS_APPROVED
    req.save(update_fields=['status'])

    # Deny all other pending requests for this company — once assigned there is nothing left to approve
    AssignmentRequest.objects.filter(
        company=req.company, status=AssignmentRequest.STATUS_PENDING
    ).update(status=AssignmentRequest.STATUS_DENIED)

    vol_name = req.volunteer.get_full_name() or req.volunteer.username
    messages.success(request, f'"{req.company.name}" assigned to {vol_name}.')
    return redirect('staff_requests')


@staff_member_required
def staff_deny_request(request, pk):
    if request.method != 'POST':
        return redirect('staff_requests')
    req = get_object_or_404(AssignmentRequest, pk=pk, status=AssignmentRequest.STATUS_PENDING)
    req.status = AssignmentRequest.STATUS_DENIED
    req.save(update_fields=['status'])
    vol_name = req.volunteer.get_full_name() or req.volunteer.username
    messages.success(request, f'Request from {vol_name} for "{req.company.name}" denied.')
    return redirect('staff_requests')


# ---------------------------------------------------------------------------
# Staff — notices
# ---------------------------------------------------------------------------

@staff_member_required
def staff_notices(request):
    notices = Notice.objects.select_related('created_by').order_by('-created_at')
    return render(request, 'core/staff_notices.html', {
        'notices': notices,
        'now':     timezone.now(),
    })


@staff_member_required
def staff_notice_form(request, pk=None):
    notice = get_object_or_404(Notice, pk=pk) if pk else None
    if request.method == 'POST':
        form = NoticeForm(request.POST, instance=notice)
        if form.is_valid():
            obj = form.save(commit=False)
            if not pk:
                obj.created_by = request.user
            obj.save()
            messages.success(request, 'Notice saved.')
            return redirect('staff_notices')
    else:
        form = NoticeForm(instance=notice)
    return render(request, 'core/staff_notice_form.html', {'form': form, 'notice': notice})


@staff_member_required
def staff_notice_delete(request, pk):
    if request.method != 'POST':
        return redirect('staff_notices')
    notice = get_object_or_404(Notice, pk=pk)
    notice.delete()
    messages.success(request, 'Notice deleted.')
    return redirect('staff_notices')


@staff_member_required
def staff_guide(request):
    return render(request, 'core/staff_guide.html')


@login_required
def volunteer_guide(request):
    return render(request, 'core/volunteer_guide.html')
