# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About the Project

EDAWN Business Builders Portal — a Django web app for managing volunteer outreach to businesses in Northern Nevada. Volunteers are assigned companies, log contact attempts and visits, and earn badges for milestones. Staff admins manage companies, assignments, volunteer accounts, and post notices to the volunteer dashboard.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server (requires SECRET_KEY env var)
SECRET_KEY=any-local-key python manage.py runserver

# System check
SECRET_KEY=any-local-key python manage.py check

# Apply migrations
python manage.py migrate

# Seed test data (creates companies, users, assignments)
python manage.py seed_data

# Create a local superuser
python manage.py createsuperuser

# Send inactivity reminder emails (run daily via Render cron job)
python manage.py send_inactivity_reminders

# Production build (Render runs this via build.sh)
./build.sh
```

There are no tests — `core/tests.py` is empty.

## Environment Variables

`SECRET_KEY` is required; the app raises `RuntimeError` at startup without it. All others are optional locally.

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | — | **Required** |
| `DEBUG` | `False` | Set to `true` for local dev |
| `DATABASE_URL` | SQLite `db.sqlite3` | Render injects PostgreSQL URL |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | |
| `CSRF_TRUSTED_ORIGINS` | — | Needed for HTTPS deployments |
| `DJANGO_SUPERUSER_PASSWORD` | — | Triggers superuser creation in `build.sh` |
| `RESEND_API_KEY` | — | Resend API key — emails are silently skipped if unset |
| `DEFAULT_FROM_EMAIL` | `EDAWN Business Builders <noreply@edawn.org>` | From address for all outgoing email |
| `SITE_URL` | `http://localhost:8000` | Used in email links — set to the public Render URL in production |
| `TRAINING_CALENDAR_URL` | Calendly link | Booking link shown on volunteer dashboard until training is marked complete |

## Architecture

**Stack:** Django 5 / Python 3.12, server-rendered templates, Bootstrap 5.3 (CDN), no JS framework. Deployed on Render with PostgreSQL + WhiteNoise for static files.

**Template layout:** All authenticated pages extend `templates/base.html`, which renders the sidebar, flash messages, and the `{% block content %}` area. Unauthenticated pages (login, password reset) use `{% block auth_content %}` — a plain centered container with no sidebar. The public landing page (`templates/core/landing.html`) is a fully standalone HTML document that does not extend `base.html`.

**URL layout:**
- `/` → volunteer dashboard (login required)
- `/about/` → public landing page
- `/login/`, `/register/`, `/logout/` → auth
- `/password-reset/`, `/password-change/` → password management
- `/companies/` → volunteer company list and detail
- `/companies/browse/` → browse unassigned companies and request assignment
- `/companies/<id>/contact/`, `/companies/<id>/visit/` → volunteer workflows
- `/badges/`, `/leaderboard/`, `/messages/`, `/resources/` → engagement and reference
- `/staff/` → staff dashboard
- `/staff/volunteers/` → volunteer roster with training/BBV/temp-password controls
- `/staff/requests/` → approve or deny company assignment requests
- `/staff/notices/` → create and manage notices shown on volunteer dashboards
- `/staff/assign/`, `/staff/add-company/`, `/staff/invite/`, `/staff/import/` → staff quick actions
- `/staff/export/` → CSV export of visit data
- `/admin/` → Django admin

**Access control:** `@login_required` on all volunteer views. `@staff_member_required` on all `/staff/` views. Private messages are filtered in the view: `is_private=True` messages are visible only to the sender, the `recipient` (if set), and staff.

## Core Data Model

The central entity is **Assignment** — it links a **Company** to a volunteer (**User**). Most other models hang off Assignment:

- **ContactAttempt** → Assignment: phone/email/in-person outreach attempts
- **VisitNote** → Assignment: records a completed visit

**Status lifecycles are driven by model `save()` hooks, not views:**

- `ContactAttempt.save()` — after 3 attempts on an active assignment, auto-sets `assignment.status = LOST` and `company.status = LOST`, then calls `check_and_award_badges(user)`.
- `VisitNote.save()` — auto-sets `assignment.status = COMPLETED`, `company.status = VISITED`, `assignment.completed_date = now()`, resets `profile.last_inactivity_notified`, and calls `check_and_award_badges(user)`.

Company status flow: `unassigned → assigned → visited / lost`
Assignment status flow: `active → completed / lost`

**Supporting models:**

- **AssignmentRequest** — a volunteer's request to be assigned an unassigned company. Capped at 3 pending requests per volunteer (non-BBV volunteers with an active assignment are blocked). Approving one auto-denies all competing requests for the same company. `unique_together = ('company', 'volunteer')`.
- **Notice** — a staff-authored announcement displayed as an alert banner on all volunteer dashboards. Requires an `expires_at` datetime; disappears automatically after expiry.
- **Resource** — a titled link (OneDrive or other URL) in a named category, visible to all volunteers on the Resources page. Staff manage these from the same page.
- **UserProfile** — one-to-one with User (created by post_save signal). Stores `bbv_certified`, `training_completed`, `last_inactivity_notified`.
- **Badge / UserBadge** — milestone achievements. Auto-awarded by `check_and_award_badges(user)` on contact/visit save. `criteria_value = 0` means manual-award only.
- **InviteCode** — single-use registration tokens. `RegisterForm` validates and consumes the code on save.
- **Message / Reply** — group board (`is_private=False`) or direct message to staff (`is_private=True`). Staff can send broadcast messages to all volunteers or filtered subsets by industry. `Message.recipient` (nullable FK) identifies the target for direct messages.

**Badge awarding** (`core/badges.py`): `check_and_award_badges(user)` runs two queries (one aggregate on Assignment, one count on ContactAttempt) and awards any threshold badges not yet earned. `check_bbv_eligibility(user)` checks whether the volunteer visited in each of the last 3 calendar months using a single filtered query.

## Rate Limiting

`core/ratelimit.py` provides a `@ratelimit(max_attempts, window, key_prefix)` decorator that tracks POST requests per client IP via Django's cache. Returns HTTP 403 on breach. Applied to: login (5/5min), register (5/5min), message_create (10/5min).

## Email Notifications

`core/emails.py` contains three helpers — all use `fail_silently=True` and are no-ops when `RESEND_API_KEY` is unset:

- `notify_volunteer_inactivity(volunteer, active_assignments, days)` — F-15, sent by cron job
- `notify_staff_volunteer_overdue(volunteer, days)` — F-16, sent by cron job, once per inactive period (guarded by `profile.last_inactivity_notified`)
- `notify_staff_visit_submitted(visit_note)` — F-17, called from `VisitNote.save()`

The cron job (`send_inactivity_reminders`) should run daily on Render. It uses `Prefetch` to avoid N+1 queries across volunteers.

## Deployment

Render runs `./build.sh` on deploy (install → collectstatic → migrate → create superuser). Static files are served by WhiteNoise. `DEBUG=False` enables HSTS, SSL redirect, and secure cookies automatically via `settings.py`.

Password reset emails require `RESEND_API_KEY`. Until that is configured, staff can issue temporary passwords directly from the volunteer roster page.
