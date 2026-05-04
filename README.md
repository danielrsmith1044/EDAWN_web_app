# EDAWN Business Builders Portal

A volunteer management web app for the Economic Development Authority of Western Nevada (EDAWN). Volunteers are assigned local businesses to visit and report on, earning badges as they hit milestones.

## Features

**Volunteer**
- **Company Browse** — Browse unassigned companies by industry and request assignment (capped at 3 pending requests)
- **Contact Tracking** — Log phone, email, and in-person contact attempts; auto-marks assignment as Lost after 3 failed attempts
- **Visit Logging** — Record structured visit notes including hiring status, employee counts, expansion signals, and follow-up needs
- **Badge System** — Achievements auto-awarded for milestones (first visit, 5 visits, 10 visits, etc.)
- **Leaderboard** — Ranks volunteers by completed visits
- **Messaging** — Group discussion board and private messages to staff, with threaded replies
- **Resources** — Staff-curated library of links (visit scripts, guides, etc.)
- **Notices** — Staff announcements displayed as banners on the volunteer dashboard

**Staff**
- **Staff Dashboard** — Stats overview, recent assignments, overdue volunteer alerts, pending request count
- **Volunteer Roster** — Full roster with training and BBV certification toggles, temporary password reset
- **Assignment Requests** — Approve or deny volunteer requests; approving one auto-denies competing requests
- **Company Management** — Add companies, bulk CSV import, assign to volunteers
- **Notices** — Create time-limited announcements with optional links; expire automatically
- **Resources** — Add, edit, and hide resource links by category
- **Visit Export** — CSV export of visit data filtered by date, industry, or volunteer
- **Expansion Signals** — Surface companies with expansion indicators from visit notes

## Tech Stack

- Python 3.12 / Django 5
- PostgreSQL (production via Render), SQLite (local dev)
- Bootstrap 5.3 + Bootstrap Icons (CDN)
- No JavaScript frameworks — server-rendered templates
- WhiteNoise for static files
- Resend SMTP for transactional email (optional)

## Local Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd EDAWN_web_app

# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
SECRET_KEY=any-local-key python manage.py migrate

# Create an admin user
SECRET_KEY=any-local-key python manage.py createsuperuser

# (Optional) Load test data
SECRET_KEY=any-local-key python manage.py seed_data

# Start the development server
SECRET_KEY=any-local-key python manage.py runserver
```

Visit `http://localhost:8000`. Log in with the superuser you created, or with a seeded volunteer account (password: `edawn2024`).

## Test Data

`python manage.py seed_data` creates:
- 6 volunteer accounts (password: `edawn2024`)
- 30 companies with varying levels of contact info
- Assignments across volunteers with visits, contact attempts, and lost cases
- Badges auto-awarded based on seeded activity

## User Roles

| Role | Access |
|------|--------|
| **Volunteer** | Dashboard, company browse/request, assigned companies, contact/visit logging, badges, leaderboard, messages, resources |
| **Staff** | All volunteer features + staff dashboard, volunteer roster, assignment request management, company management, notices, resource management, CSV import/export, invite links |

## Management Commands

| Command | Purpose |
|---------|---------|
| `python manage.py seed_data` | Populate database with test data |
| `python manage.py createsuperuser` | Create an admin account |
| `python manage.py send_inactivity_reminders` | Email volunteers inactive 30+ days; alert staff at 45+ days (run daily via Render cron job) |

## Environment Variables

| Variable | Required | Notes |
|----------|----------|-------|
| `SECRET_KEY` | Yes | Any long random string |
| `DEBUG` | No | Set to `true` for local dev |
| `DATABASE_URL` | No | Defaults to SQLite; Render injects PostgreSQL URL |
| `ALLOWED_HOSTS` | No | Defaults to `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | No | Required for HTTPS deployments |
| `DJANGO_SUPERUSER_PASSWORD` | No | Triggers superuser creation in `build.sh` |
| `RESEND_API_KEY` | No | Enables transactional email; silently skipped if unset |
| `DEFAULT_FROM_EMAIL` | No | Defaults to `EDAWN Business Builders <noreply@edawn.org>` |
| `SITE_URL` | No | Public URL used in email links; defaults to `http://localhost:8000` |
| `TRAINING_CALENDAR_URL` | No | Calendly booking link shown until training is marked complete |

## Deployment (Render)

`./build.sh` runs on each deploy: install dependencies → collectstatic → migrate → create superuser (if `DJANGO_SUPERUSER_PASSWORD` is set).

Add a daily cron job on Render running `python manage.py send_inactivity_reminders` to send volunteer inactivity reminders once email is configured.

## Project Structure

```
edawn/              Django project settings and root URLs
core/               Main app
  models.py         All data models
  views.py          All views (volunteer + staff)
  forms.py          All forms
  badges.py         Badge award logic
  emails.py         Email notification helpers
  admin.py          Django admin configuration
  ratelimit.py      IP-based rate limiting decorator
  management/       Custom management commands
templates/
  base.html         Authenticated layout (sidebar + flash messages)
  core/             App templates
  registration/     Login, register, password reset/change
static/             Logo and font assets
```
