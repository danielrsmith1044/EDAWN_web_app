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
