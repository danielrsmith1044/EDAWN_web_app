from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Q

from .models import Company, Assignment, ContactAttempt, VisitNote, Goal
from .forms import RegisterForm, ContactAttemptForm, VisitNoteForm, GoalProgressForm


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

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
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


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
    context = {
        'active_assignments': active_assignments,
        'my_goals':        Goal.objects.filter(user=user),
        'top_users':       _leaderboard_qs()[:5],
        'total_assigned':  Assignment.objects.filter(volunteer=user).count(),
        'completed_count': Assignment.objects.filter(volunteer=user, status=Assignment.STATUS_COMPLETED).count(),
        'lost_count':      Assignment.objects.filter(volunteer=user, status=Assignment.STATUS_LOST).count(),
        'open_count':      active_assignments.count(),
    }
    return render(request, 'core/dashboard.html', context)


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
# Goals
# ---------------------------------------------------------------------------

@login_required
def goal_list(request):
    goals = Goal.objects.filter(user=request.user)
    return render(request, 'core/goal_list.html', {'goals': goals})


@login_required
def goal_detail(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        form = GoalProgressForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Goal progress updated.')
            return redirect('goal_detail', pk=goal.pk)
    else:
        form = GoalProgressForm(instance=goal)
    return render(request, 'core/goal_detail.html', {'goal': goal, 'form': form})


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

@login_required
def leaderboard(request):
    return render(request, 'core/leaderboard.html', {'users': _leaderboard_qs()})
