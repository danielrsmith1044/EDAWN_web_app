import uuid
from urllib.parse import quote_plus

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Count, Q


class Company(models.Model):
    STATUS_UNASSIGNED = 'unassigned'
    STATUS_ASSIGNED   = 'assigned'
    STATUS_VISITED    = 'visited'
    STATUS_LOST       = 'lost'
    STATUS_CHOICES = [
        (STATUS_UNASSIGNED, 'Unassigned'),
        (STATUS_ASSIGNED,   'Assigned'),
        (STATUS_VISITED,    'Visited'),
        (STATUS_LOST,       'Lost'),
    ]

    name                  = models.CharField(max_length=255)
    address               = models.CharField(max_length=255, blank=True)
    city                  = models.CharField(max_length=100, blank=True)
    state                 = models.CharField(max_length=50,  blank=True)
    zip_code              = models.CharField(max_length=20,  blank=True)
    phone                 = models.CharField(max_length=50,  blank=True)
    email                 = models.EmailField(blank=True)
    website               = models.URLField(blank=True)
    industry              = models.CharField(max_length=100, blank=True)
    primary_contact_name  = models.CharField(max_length=100, blank=True)
    primary_contact_title = models.CharField(max_length=100, blank=True)
    notes                 = models.TextField(blank=True, help_text="Internal admin notes")
    status                = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UNASSIGNED)
    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Companies'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def maps_url(self):
        parts = filter(None, [self.address, self.city, self.state, self.zip_code])
        query = ', '.join(parts)
        if not query:
            return None
        return f'https://www.google.com/maps/search/?api=1&query={quote_plus(query)}'

    @property
    def active_assignment(self):
        return self.assignments.filter(status=Assignment.STATUS_ACTIVE).first()


class Assignment(models.Model):
    STATUS_ACTIVE    = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_LOST      = 'lost'
    STATUS_CHOICES = [
        (STATUS_ACTIVE,    'Active'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_LOST,      'Lost'),
    ]

    company        = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='assignments')
    volunteer      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments')
    assigned_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='assignments_given')
    assigned_date  = models.DateTimeField(auto_now_add=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    completed_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-assigned_date']

    def __str__(self):
        name = self.volunteer.get_full_name() or self.volunteer.username
        return f"{self.company.name} → {name}"

    @property
    def contact_attempt_count(self):
        return self.contact_attempts.count()

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE


class ContactAttempt(models.Model):
    METHOD_CHOICES = [
        ('phone',     'Phone'),
        ('email',     'Email'),
        ('in_person', 'In Person'),
        ('other',     'Other'),
    ]

    assignment   = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='contact_attempts')
    attempted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    attempt_date = models.DateTimeField(auto_now_add=True)
    method       = models.CharField(max_length=20, choices=METHOD_CHOICES, default='phone')
    notes        = models.TextField(blank=True)

    class Meta:
        ordering = ['-attempt_date']

    def __str__(self):
        return f"Attempt on {self.assignment.company.name} ({self.attempt_date.date()})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Auto-mark lost after 3 failed contact attempts
        if (self.assignment.contact_attempts.count() >= 3
                and self.assignment.status == Assignment.STATUS_ACTIVE):
            self.assignment.status = Assignment.STATUS_LOST
            self.assignment.save(update_fields=['status'])
            self.assignment.company.status = Company.STATUS_LOST
            self.assignment.company.save(update_fields=['status'])
        # Check for badge awards
        from .badges import check_and_award_badges
        check_and_award_badges(self.attempted_by)


class VisitNote(models.Model):
    HIRING_STATUS_CHOICES = [
        ('hiring',  'Actively Hiring'),
        ('layoffs', 'Layoffs Occurring'),
        ('stable',  'Stable / No Change'),
        ('unknown', 'Unknown'),
    ]
    AT_CAPACITY_CHOICES = [
        ('',    'Unknown'),
        ('yes', 'Yes — at capacity'),
        ('no',  'No — room to grow'),
    ]

    assignment       = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='visit_notes')
    visited_by       = models.ForeignKey(User, on_delete=models.CASCADE)
    visit_date       = models.DateTimeField(auto_now_add=True)

    # Who was spoken to
    contact_name = models.CharField(max_length=100, blank=True, verbose_name='Contact spoken to')

    # Additional contact captured during visit
    additional_contact_name  = models.CharField(max_length=100, blank=True)
    additional_contact_title = models.CharField(max_length=100, blank=True)
    additional_contact_phone = models.CharField(max_length=50,  blank=True)
    additional_contact_email = models.EmailField(blank=True)

    # General visit notes
    notes = models.TextField()

    # Workforce data (F-10/F-11)
    hiring_status       = models.CharField(max_length=10, choices=HIRING_STATUS_CHOICES, blank=True,
                                           verbose_name='Hiring / layoff status')
    employee_count      = models.PositiveIntegerField(null=True, blank=True, verbose_name='Current employees')
    jobs_added_expected = models.PositiveIntegerField(null=True, blank=True, verbose_name='Expected jobs to be added')
    jobs_added_last_year = models.PositiveIntegerField(null=True, blank=True, verbose_name='Jobs added last year')
    jobs_lost_last_year  = models.PositiveIntegerField(null=True, blank=True, verbose_name='Jobs lost last year')

    # Facility
    building_size_sqft = models.PositiveIntegerField(null=True, blank=True, verbose_name='Current building size (sq ft)')
    at_capacity        = models.CharField(max_length=3, choices=AT_CAPACITY_CHOICES, blank=True,
                                          verbose_name='At capacity?')

    # Expansion opportunity flags (F-32)
    expansion_adding_sq_footage = models.BooleanField(default=False, verbose_name='Adding square footage')
    expansion_new_building      = models.BooleanField(default=False, verbose_name='Looking for / moving to new building')
    expansion_adding_equipment  = models.BooleanField(default=False, verbose_name='Adding equipment')
    expansion_capex_planned     = models.BooleanField(default=False, verbose_name='Capital expenditure planned')
    expansion_notes             = models.TextField(blank=True, verbose_name='Expansion details')

    # Volunteer helped the company
    volunteer_helped       = models.BooleanField(default=False, verbose_name='I assisted this company with a problem during this visit')
    volunteer_helped_notes = models.TextField(blank=True, verbose_name='How did you assist?')

    # Volunteer business lead tracking (F-35)
    received_business_lead = models.BooleanField(default=False, verbose_name='Received a business lead or referral')

    # Follow-up
    follow_up_needed = models.BooleanField(default=False)
    follow_up_notes  = models.TextField(blank=True)

    class Meta:
        ordering = ['-visit_date']

    def __str__(self):
        return f"Visit to {self.assignment.company.name} ({self.visit_date.date()})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Mark assignment and company as visited/completed
        if self.assignment.status == Assignment.STATUS_ACTIVE:
            from django.utils import timezone
            self.assignment.status = Assignment.STATUS_COMPLETED
            self.assignment.completed_date = timezone.now()
            self.assignment.save(update_fields=['status', 'completed_date'])
            self.assignment.company.status = Company.STATUS_VISITED
            self.assignment.company.save(update_fields=['status'])
        # Check for badge awards
        from .badges import check_and_award_badges
        check_and_award_badges(self.visited_by)


class Badge(models.Model):
    CRITERIA_CHOICES = [
        ('visits_completed',    'Visits Completed'),
        ('contact_attempts',    'Contact Attempts Logged'),
        ('assignments_received', 'Assignments Received'),
        ('manual',              'Manually Awarded'),
    ]

    name            = models.CharField(max_length=100, unique=True)
    description     = models.TextField()
    icon            = models.CharField(max_length=50, help_text="Bootstrap icon class, e.g. bi-star")
    color           = models.CharField(max_length=7, default='#008b99', help_text="Hex color for the badge")
    criteria_type   = models.CharField(max_length=30, choices=CRITERIA_CHOICES, default='manual')
    criteria_value  = models.PositiveIntegerField(
        default=0,
        help_text="Threshold to auto-award (0 = manual only)",
    )
    sort_order      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='earned_badges')
    badge     = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awards')
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-earned_at']

    def __str__(self):
        return f"{self.user.username} — {self.badge.name}"


class Message(models.Model):
    sender     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_sent')
    subject    = models.CharField(max_length=200)
    body       = models.TextField()
    is_private = models.BooleanField(
        default=False,
        help_text="Private messages are only visible to admins and the sender",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.subject

    @property
    def reply_count(self):
        return self.replies.count()


class Reply(models.Model):
    message    = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='replies')
    sender     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='replies_sent')
    body       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Replies'

    def __str__(self):
        return f"Reply to \"{self.message.subject}\" by {self.sender.username}"


class InviteCode(models.Model):
    code       = models.CharField(max_length=40, unique=True, default=uuid.uuid4)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='invites_created')
    used_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invite_used')
    created_at = models.DateTimeField(auto_now_add=True)
    used_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = f"used by {self.used_by.username}" if self.used_by else "available"
        return f"{str(self.code)[:8]}… ({status})"

    @property
    def is_available(self):
        return self.used_by is None
