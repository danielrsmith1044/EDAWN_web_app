def check_and_award_badges(user):
    """Check all auto-award badges and grant any the user has earned."""
    from .models import Assignment, Badge, ContactAttempt, Message, UserBadge

    already_earned = set(
        UserBadge.objects.filter(user=user).values_list('badge_id', flat=True)
    )

    from django.db.models import Count, Q as _Q
    assignment_stats = Assignment.objects.filter(volunteer=user).aggregate(
        visits_completed=Count('pk', filter=_Q(status=Assignment.STATUS_COMPLETED)),
        assignments_received=Count('pk'),
    )
    stats = {
        'visits_completed':    assignment_stats['visits_completed'],
        'contact_attempts':    ContactAttempt.objects.filter(attempted_by=user).count(),
        'assignments_received': assignment_stats['assignments_received'],
    }

    auto_badges = Badge.objects.exclude(criteria_type='manual').exclude(criteria_value=0)
    newly_earned = []

    for badge in auto_badges:
        if badge.pk in already_earned:
            continue
        user_value = stats.get(badge.criteria_type, 0)
        if user_value >= badge.criteria_value:
            UserBadge.objects.create(user=user, badge=badge)
            newly_earned.append(badge)

    # Post a group message for each newly earned badge
    display_name = user.get_full_name() or user.username
    for badge in newly_earned:
        Message.objects.create(
            sender=user,
            subject=f"Badge Earned: {badge.name}",
            body=f"{display_name} just earned the \"{badge.name}\" badge! {badge.description}",
            is_private=False,
        )

    return newly_earned


def check_bbv_eligibility(user):
    """Award Certified BBV designation if volunteer visited in each of the last 3 calendar months."""
    from .models import Badge, Message, UserBadge, UserProfile, VisitNote
    from django.db.models import Q
    from django.utils import timezone

    profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.bbv_certified:
        return

    now = timezone.now()
    required = []
    for i in range(1, 4):
        m, y = now.month - i, now.year
        if m <= 0:
            m += 12
            y -= 1
        required.append((y, m))

    month_q = Q()
    for y, m in required:
        month_q |= Q(visit_date__year=y, visit_date__month=m)

    covered = set(
        VisitNote.objects.filter(visited_by=user).filter(month_q)
        .values_list('visit_date__year', 'visit_date__month').distinct()
    )
    if not all((y, m) in covered for y, m in required):
        return

    profile.bbv_certified      = True
    profile.bbv_certified_date = now
    profile.save(update_fields=['bbv_certified', 'bbv_certified_date'])

    bbv_badge = Badge.objects.filter(name='Certified Business Builder Volunteer').first()
    if bbv_badge:
        UserBadge.objects.get_or_create(user=user, badge=bbv_badge)

    display_name = user.get_full_name() or user.username
    Message.objects.create(
        sender=user,
        subject=f'{display_name} earned Certified BBV!',
        body=(
            f'{display_name} has completed 3 consecutive months of active volunteering '
            f'and earned the Certified Business Builder Volunteer (BBV) designation!'
        ),
        is_private=True,
    )
