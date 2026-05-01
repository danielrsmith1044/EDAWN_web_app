def check_and_award_badges(user):
    """Check all auto-award badges and grant any the user has earned."""
    from .models import Assignment, Badge, ContactAttempt, Message, UserBadge

    already_earned = set(
        UserBadge.objects.filter(user=user).values_list('badge_id', flat=True)
    )

    stats = {
        'visits_completed': (
            Assignment.objects
            .filter(volunteer=user, status=Assignment.STATUS_COMPLETED)
            .count()
        ),
        'contact_attempts': (
            ContactAttempt.objects
            .filter(attempted_by=user)
            .count()
        ),
        'assignments_received': (
            Assignment.objects
            .filter(volunteer=user)
            .count()
        ),
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
    from django.utils import timezone

    profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.bbv_certified:
        return

    now = timezone.now()
    for months_back in range(1, 4):
        month = now.month - months_back
        year  = now.year
        while month <= 0:
            month += 12
            year  -= 1
        if not VisitNote.objects.filter(
            visited_by=user,
            visit_date__year=year,
            visit_date__month=month,
        ).exists():
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
