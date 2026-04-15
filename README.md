# EDAWN Business Builders Portal

A volunteer management web app for the Economic Development Authority of Western Nevada (EDAWN). Volunteers are assigned companies to visit and report on, earning badges as they hit milestones.

## Features

- **Company Assignment** — Admins assign companies to volunteers via the admin panel or CSV import
- **Contact Tracking** — Volunteers log phone, email, and in-person contact attempts (auto-marks as Lost after 3 failed attempts)
- **Visit Logging** — Record visit notes with optional follow-up tracking (auto-marks company as Visited)
- **Badge System** — Gamified achievements auto-awarded for milestones (first visit, 5 visits, 10 visits, etc.)
- **Messaging** — Group discussion board and private messages to admin, with threaded replies
- **Leaderboard** — Ranks volunteers by completed visits
- **Admin Dashboard** — Custom admin interface with quick actions, stats overview, and recent activity
- **CSV Import** — Bulk import companies from a CSV file with flexible column mapping

## Tech Stack

- Python 3.12 / Django 5.0
- SQLite (development)
- Bootstrap 5.3 / Bootstrap Icons
- No JavaScript frameworks — server-rendered templates

## Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd EDAWN_web_app

# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create an admin user
python manage.py createsuperuser

# (Optional) Load test data — creates 6 volunteers, 30 companies, and sample activity
python manage.py seed_data

# Start the development server
python manage.py runserver
```

## Test Data

The `seed_data` command creates:
- 6 volunteer accounts (password: `edawn2024`)
- 30 companies with varying levels of contact info
- Assignments across volunteers with visits, contact attempts, and lost cases
- Badges auto-awarded based on seeded activity

## User Roles

| Role | Access |
|------|--------|
| **Volunteer** | Dashboard, assigned companies, contact/visit logging, badges, messages, leaderboard |
| **Admin (staff)** | All volunteer features + admin panel, company management, CSV import, volunteer assignment, badge management, all private messages |

## Project Structure

```
edawn/              Django project settings
core/               Main app (models, views, forms, admin, badges)
templates/          HTML templates (base, core/, registration/, admin/)
static/img/         Logo assets
manage.py           Django management script
```

## Management Commands

- `python manage.py seed_data` — Populate database with test data
- `python manage.py createsuperuser` — Create an admin account
