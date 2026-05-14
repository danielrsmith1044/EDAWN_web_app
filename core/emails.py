from django.conf import settings
from django.core.mail import send_mail


def _portal_url(path=''):
    return f"{settings.SITE_URL.rstrip('/')}{path}"


def notify_volunteer_inactivity(volunteer, active_assignments, days_since_visit):
    """F-15: Remind volunteer they have active assignments with no recent visit."""
    company_list = '\n'.join(f'  • {a.company.name}' for a in active_assignments)
    first_name = volunteer.first_name or volunteer.username
    send_mail(
        subject='Reminder: Your assigned companies are waiting for a visit',
        message=(
            f"Hi {first_name},\n\n"
            f"It's been {days_since_visit} days since your last visit. "
            f"Your active companies are counting on you!\n\n"
            f"{company_list}\n\n"
            f"Log in to the portal to plan your next visit:\n"
            f"{_portal_url()}\n\n"
            f"Thanks for your work,\n"
            f"EDAWN Business Builders"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[volunteer.email],
        fail_silently=True,
    )


def notify_staff_volunteer_overdue(volunteer, days_since_visit):
    """F-16: Alert staff that a volunteer has been inactive 45+ days."""
    staff_emails = _staff_emails()
    if not staff_emails:
        return
    name = volunteer.get_full_name() or volunteer.username
    send_mail(
        subject=f'Volunteer overdue: {name} ({days_since_visit} days inactive)',
        message=(
            f"{name} has active company assignments but has not logged a visit "
            f"in {days_since_visit} days.\n\n"
            f"Review their status on the volunteer roster:\n"
            f"{_portal_url('/staff/volunteers/')}\n\n"
            f"— EDAWN Portal"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=staff_emails,
        fail_silently=True,
    )


def notify_staff_visit_submitted(visit_note):
    """F-17: Notify staff when a volunteer logs a visit."""
    if not settings.EMAIL_HOST_PASSWORD:
        return
    staff_emails = _staff_emails()
    if not staff_emails:
        return
    company  = visit_note.assignment.company
    vol      = visit_note.visited_by
    vol_name = vol.get_full_name() or vol.username
    send_mail(
        subject=f'Visit logged: {company.name} by {vol_name}',
        message=(
            f"{vol_name} just logged a visit to {company.name}.\n\n"
            f"Hiring status: {visit_note.get_hiring_status_display() if visit_note.hiring_status else 'Not recorded'}\n"
            f"Employees: {visit_note.employee_count or 'Not recorded'}\n\n"
            f"View the full visit note:\n"
            f"{_portal_url(f'/companies/{visit_note.assignment.pk}/')}\n\n"
            f"— EDAWN Portal"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=staff_emails,
        fail_silently=True,
    )


def notify_admin_welcome(user, reset_link):
    """Send a new admin their account details and a password-set link."""
    name = user.first_name or user.username
    send_mail(
        subject='Your EDAWN Business Builders admin account is ready',
        message=(
            f"Hi {name},\n\n"
            f"An admin account has been created for you on the EDAWN Business Builders portal.\n\n"
            f"Username: {user.username}\n\n"
            f"Set your password and log in here:\n"
            f"{reset_link}\n\n"
            f"This link expires in 24 hours. If you have questions, contact kim.yaegar@edawn.org.\n\n"
            f"— EDAWN Business Builders"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def notify_invite(email, invite_link):
    """Send a registration invite link directly to a prospective volunteer."""
    send_mail(
        subject='You\'ve been invited to EDAWN Business Builders',
        message=(
            f"You've been invited to join the EDAWN Business Builders volunteer portal.\n\n"
            f"Click the link below to create your account:\n"
            f"{invite_link}\n\n"
            f"This link can only be used once. If you have any questions, "
            f"contact kim.yaegar@edawn.org.\n\n"
            f"— EDAWN Business Builders"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def _staff_emails():
    from django.contrib.auth.models import User
    return list(
        User.objects.filter(is_staff=True, is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )
