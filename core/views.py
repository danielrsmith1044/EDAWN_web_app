from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Q

from .models import Company, Assignment, ContactAttempt, InviteCode, VisitNote, Badge, UserBadge, Message, Reply
from .forms import (RegisterForm, ContactAttemptForm, VisitNoteForm, MessageForm, ReplyForm,
                     QuickCompanyForm, QuickAssignForm, CreateAdminForm)
from .ratelimit import ratelimit


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

    # Admin tools — only for staff users
    if user.is_staff:
        context['unassigned_count'] = Company.objects.filter(status=Company.STATUS_UNASSIGNED).count()

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
            Assignment.objects.create(
                company=company,
                volunteer=volunteer,
                assigned_by=request.user,
            )
            company.status = Company.STATUS_ASSIGNED
            company.save(update_fields=['status'])
            vol_name = volunteer.get_full_name() or volunteer.username
            messages.success(request, f'"{company.name}" assigned to {vol_name}.')
            return redirect('quick_assign')
    else:
        form = QuickAssignForm()
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
        'invite_link': invite_link,
        'available': available,
    })


# ---------------------------------------------------------------------------
# Companies / Assignments
# ---------------------------------------------------------------------------

@login_required
def company_list(request):
    status_filter = request.GET.get('status', 'active')
    assignments = Assignment.objects.filter(volunteer=request.user).select_related('company')

    if status_filter == 'active':
        assignments = assignments.filter(status=Assignment.STATUS_ACTIVE)
    elif status_filter == 'completed':
        assignments = assignments.filter(status=Assignment.STATUS_COMPLETED)
    elif status_filter == 'lost':
        assignments = assignments.filter(status=Assignment.STATUS_LOST)
    # 'all' returns everything

    context = {
        'assignments':   assignments.order_by('company__name'),
        'status_filter': status_filter,
    }
    return render(request, 'core/company_list.html', context)


@login_required
def company_detail(request, pk):
    assignment       = get_object_or_404(Assignment, pk=pk, volunteer=request.user)
    contact_attempts = assignment.contact_attempts.all()
    visit_notes      = assignment.visit_notes.all()

    context = {
        'assignment':         assignment,
        'company':            assignment.company,
        'contact_attempts':   contact_attempts,
        'visit_notes':        visit_notes,
        'contact_form':       ContactAttemptForm(),
        'attempts_remaining': max(0, 3 - contact_attempts.count()),
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

    if not assignment.is_active:
        messages.error(request, "This assignment is no longer active.")
        return redirect('company_detail', pk=pk)

    if request.method == 'POST':
        form = VisitNoteForm(request.POST)
        if form.is_valid():
            note            = form.save(commit=False)
            note.assignment = assignment
            note.visited_by = request.user
            note.save()
            messages.success(request, f"Visit to {assignment.company.name} recorded!")
            return redirect('company_detail', pk=pk)
    else:
        form = VisitNoteForm()

    return render(request, 'core/log_visit.html', {
        'assignment': assignment,
        'company':    assignment.company,
        'form':       form,
    })


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------

@login_required
def badge_list(request):
    all_badges = Badge.objects.all()
    earned_ids = set(
        UserBadge.objects
        .filter(user=request.user)
        .values_list('badge_id', flat=True)
    )
    earned_map = {
        ub.badge_id: ub.earned_at
        for ub in UserBadge.objects.filter(user=request.user)
    }
    badges = []
    for badge in all_badges:
        badges.append({
            'badge': badge,
            'earned': badge.pk in earned_ids,
            'earned_at': earned_map.get(badge.pk),
        })
    context = {
        'badges': badges,
        'earned_count': len(earned_ids),
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
            qs = Message.objects.filter(is_private=True, sender=user)
    else:
        # group (public) messages
        qs = Message.objects.filter(is_private=False)

    context = {
        'messages_list': qs.select_related('sender'),
        'filter_type':   filter_type,
    }
    return render(request, 'core/message_list.html', context)


@login_required
def message_detail(request, pk):
    message = get_object_or_404(Message, pk=pk)

    # Access control: private messages visible only to sender and staff
    if message.is_private and not request.user.is_staff and message.sender != request.user:
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
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
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
    return render(request, 'core/message_create.html', {'form': form})
