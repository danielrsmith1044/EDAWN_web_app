"""
Management command: python manage.py seed_data

Creates realistic test data:
  - 6 volunteer users
  - 30 companies (varying levels of info)
  - Assignments spread across volunteers
  - Contact attempts (some leading to Lost)
  - Visit notes (marking companies Visited)
  - Goals for each volunteer
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Assignment, Company, ContactAttempt, Goal, VisitNote


VOLUNTEERS = [
    ("jsmith",    "Jane",    "Smith",    "jsmith@edawn.org"),
    ("mjohnson",  "Marcus",  "Johnson",  "mjohnson@edawn.org"),
    ("aproctor",  "Alicia",  "Proctor",  "aproctor@edawn.org"),
    ("twilliams", "Tom",     "Williams", "twilliams@edawn.org"),
    ("slee",      "Sara",    "Lee",      "slee@edawn.org"),
    ("dgarcia",   "Diego",   "Garcia",   "dgarcia@edawn.org"),
]

COMPANIES = [
    # (name, address, city, state, zip, phone, email, website, industry, contact_name, contact_title)
    ("Acme Manufacturing",       "100 Industrial Blvd",  "Reno",   "NV", "89501", "775-555-0101", "info@acme.com",       "https://acme.com",       "Manufacturing",   "Robert Hall",    "Plant Manager"),
    ("Sierra Nevada Brewing",    "1075 E 20th St",       "Reno",   "NV", "89512", "775-555-0102", "contact@snbrewing.com","",                      "Food & Beverage", "Lisa Tran",      "Operations Dir."),
    ("Reno Logistics Group",     "2200 Vassar St",       "Reno",   "NV", "89502", "775-555-0103", "",                    "",                       "Transportation",  "Mike Pearson",   "CEO"),
    ("TechBridge Solutions",     "500 E Liberty St",     "Reno",   "NV", "89501", "775-555-0104", "hr@techbridge.com",   "https://techbridge.io",  "Technology",      "Amy Chen",       "HR Director"),
    ("High Desert Health",       "3300 W Plumb Ln",      "Reno",   "NV", "89509", "775-555-0105", "",                    "",                       "Healthcare",      "Dr. Paul Ruiz",  "Medical Director"),
    ("Sparks Steel & Supply",    "800 Marietta Way",     "Sparks", "NV", "89431", "775-555-0106", "sales@sparksss.com",  "",                       "Manufacturing",   "Gary Stone",     "Sales Manager"),
    ("Nevada Solar Partners",    "1400 S Virginia St",   "Reno",   "NV", "89502", "775-555-0107", "info@nvsolar.com",    "https://nvsolar.com",    "Energy",          "Karen Mills",    "President"),
    ("Great Basin Distributors", "610 Spice Islands Dr", "Sparks", "NV", "89431", "775-555-0108", "",                    "",                       "Wholesale",       "James Ford",     "VP Operations"),
    ("Tahoe Financial Group",    "100 W Liberty St",     "Reno",   "NV", "89501", "775-555-0109", "contact@tahoefg.com", "https://tahoefg.com",    "Finance",         "Susan Park",     "Branch Manager"),
    ("Mountain West Realty",     "4895 Double R Blvd",   "Reno",   "NV", "89521", "775-555-0110", "",                    "",                       "Real Estate",     "Chris Dunbar",   "Broker"),
    ("Reno Air Transport",       "2001 E Plumb Ln",      "Reno",   "NV", "89502", "775-555-0111", "ops@renoair.com",     "",                       "Transportation",  "Phil Nguyen",    "Station Manager"),
    ("Basin Mining Co.",         "7200 Longley Ln",      "Reno",   "NV", "89511", "775-555-0112", "",                    "",                       "Mining",          "",               ""),
    ("Neon Valley Media",        "299 S Virginia St",    "Reno",   "NV", "89501", "775-555-0113", "hello@neonvm.com",    "https://neonvm.com",     "Media",           "Tina Ross",      "Creative Dir."),
    ("Silver State Staffing",    "1 E 1st St",           "Reno",   "NV", "89501", "775-555-0114", "",                    "",                       "Staffing",        "Brenda Walsh",   "Recruiter"),
    ("Legends Hospitality",      "255 N Sierra St",      "Reno",   "NV", "89501", "775-555-0115", "gm@legendshotel.com", "https://legendshotel.com","Hospitality",    "Marco Vitale",   "General Manager"),
    ("Western Ag Supply",        "5600 Mill St",         "Sparks", "NV", "89431", "775-555-0116", "",                    "",                       "Agriculture",     "Dale Horton",    "Owner"),
    ("Summit Data Center",       "9350 Gateway Dr",      "Reno",   "NV", "89521", "775-555-0117", "info@summitdc.com",   "https://summitdc.com",   "Technology",      "Rachel Kim",     "Facilities Mgr"),
    ("Clearwater Consulting",    "400 W 4th St",         "Reno",   "NV", "89503", "775-555-0118", "",                    "",                       "Consulting",      "Aaron Bell",     "Principal"),
    ("NV Craft Spirits",         "1045 E 4th St",        "Reno",   "NV", "89512", "775-555-0119", "tours@nvcraft.com",   "",                       "Food & Beverage", "Molly Grant",    "Distillery Mgr"),
    ("Desert Wind Construction", "3800 Barron Way",      "Reno",   "NV", "89511", "", "",                                "",                       "Construction",    "",               ""),
    ("Pioneer Equipment Rental", "1760 E Commercial Row","Reno",   "NV", "89502", "775-555-0121", "",                    "",                       "Equipment Rental","Todd Barnes",    "Owner"),
    ("Alpine Insurance Group",   "10 Liberty St",        "Reno",   "NV", "89501", "775-555-0122", "info@alpineins.com",  "https://alpineins.com",  "Insurance",       "Nancy Flores",   "Agent"),
    ("Reno Print & Design",      "522 W 5th St",         "Reno",   "NV", "89503", "775-555-0123", "",                    "",                       "Printing",        "Kevin Shaw",     "Owner"),
    ("Cascade Tech Partners",    "6900 S McCarran Blvd", "Reno",   "NV", "89509", "775-555-0124", "info@cascadetp.com",  "https://cascadetp.com",  "Technology",      "Yuki Tanaka",    "Director"),
    ("Basin Biomedical",         "1670 Rupert St",       "Reno",   "NV", "89502", "775-555-0125", "",                    "",                       "Healthcare",      "Dr. Maria Soto", "Lab Director"),
    ("Truckee River Brewing",    "1 Stokes St",          "Reno",   "NV", "89501", "775-555-0126", "hello@trbrew.com",    "https://trbrew.com",     "Food & Beverage", "Sam Kowalski",   "Head Brewer"),
    ("NV Fleet Services",        "2300 Harvard Way",     "Reno",   "NV", "89502", "", "",                                "",                       "Transportation",  "",               ""),
    ("Ridgeline Architecture",   "50 Washington St",     "Reno",   "NV", "89503", "775-555-0128", "design@ridgeline.com","https://ridgeline.com",  "Architecture",    "Claire Webb",    "Principal Arch."),
    ("Pyramid Lake Fisheries",   "2100 Pyramid Way",     "Sparks", "NV", "89436", "775-555-0129", "",                    "",                       "Agriculture",     "Tribal Contact", ""),
    ("Washoe County Creamery",   "890 Record St",        "Reno",   "NV", "89512", "775-555-0130", "milk@washoecream.com","",                       "Food & Beverage", "Pete Crawford",  "Owner"),
]


VISIT_NOTES_TEXTS = [
    "Met with the operations manager. Company is actively hiring and interested in EDAWN's workforce development programs. Follow-up with training info requested.",
    "Spoke with owner directly. Business has grown 20% this year. Open to future partnerships and events. Very receptive to our outreach.",
    "Toured the facility. About 45 employees on site. They use local suppliers and expressed interest in our supplier network program.",
    "Quick visit — GM was busy but friendly. Left materials. They will review and may attend next quarterly event.",
    "Had a great 45-minute conversation with the director. They're planning to expand and want to know more about incentive programs. Set up a follow-up call.",
    "Visited during lunch rush. Owner said things are going well. Small operation, not in immediate need of services but appreciates the outreach.",
    "Met the HR director who was very interested in our job fair. Committed to participating in the next one. Will send company profile.",
    "Company is newer — only 2 years old. Founder gave a tour of the space. Interested in networking events to meet other businesses.",
]

CONTACT_NOTES_TEXTS = [
    "Called main line, no answer. Left voicemail.",
    "Emailed contact — no response after 3 days.",
    "Stopped by — office was closed, left a business card.",
    "Called twice, went to voicemail both times.",
    "Sent follow-up email, no reply.",
    "Attempted in person visit, receptionist said contact was out of office.",
]


class Command(BaseCommand):
    help = "Populate the database with realistic test data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding test data...")

        # ----------------------------------------------------------------
        # Volunteers
        # ----------------------------------------------------------------
        volunteers = []
        for username, first, last, email in VOLUNTEERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults=dict(first_name=first, last_name=last, email=email),
            )
            if created:
                user.set_password("edawn2024")
                user.save()
            volunteers.append(user)
        self.stdout.write(f"  {len(volunteers)} volunteers ready")

        admin = User.objects.filter(is_superuser=True).first()

        # ----------------------------------------------------------------
        # Companies
        # ----------------------------------------------------------------
        companies = []
        for row in COMPANIES:
            name, address, city, state, zip_code, phone, email, website, industry, contact_name, contact_title = row
            co, _ = Company.objects.get_or_create(
                name=name,
                defaults=dict(
                    address=address, city=city, state=state, zip_code=zip_code,
                    phone=phone, email=email, website=website, industry=industry,
                    primary_contact_name=contact_name, primary_contact_title=contact_title,
                ),
            )
            companies.append(co)
        self.stdout.write(f"  {len(companies)} companies ready")

        # ----------------------------------------------------------------
        # Goals for each volunteer
        # ----------------------------------------------------------------
        goal_templates = [
            ("Visit 10 Companies",  10, 0),
            ("Contact Attempts",    20, 0),
        ]
        for vol in volunteers:
            for title, target, current in goal_templates:
                Goal.objects.get_or_create(user=vol, title=title, defaults=dict(
                    target_value=target, current_value=current,
                ))

        # ----------------------------------------------------------------
        # Assignments — spread companies across volunteers
        # Scenario breakdown across 30 companies:
        #   6  visited
        #   4  lost (3 contact attempts each)
        #   20 active (various contact attempt counts)
        # ----------------------------------------------------------------
        if Assignment.objects.exists():
            self.stdout.write("  Assignments already exist — skipping assignment seeding.")
            self.stdout.write(self.style.SUCCESS("Done."))
            return

        import itertools
        vol_cycle = itertools.cycle(volunteers)

        for i, company in enumerate(companies):
            volunteer = next(vol_cycle)

            assignment = Assignment.objects.create(
                company=company,
                volunteer=volunteer,
                assigned_by=admin,
            )

            if i < 6:
                # --- Visited ---
                note_text = VISIT_NOTES_TEXTS[i % len(VISIT_NOTES_TEXTS)]
                VisitNote.objects.create(
                    assignment=assignment,
                    visited_by=volunteer,
                    notes=note_text,
                    follow_up_needed=(i % 3 == 0),
                    follow_up_notes="Send program brochure and invite to next networking event." if i % 3 == 0 else "",
                )

            elif i < 10:
                # --- Lost (3 attempts) ---
                for j in range(3):
                    methods = ['phone', 'email', 'in_person']
                    ContactAttempt.objects.create(
                        assignment=assignment,
                        attempted_by=volunteer,
                        method=methods[j % 3],
                        notes=CONTACT_NOTES_TEXTS[j % len(CONTACT_NOTES_TEXTS)],
                    )
                # Status set automatically by ContactAttempt.save()

            elif i < 15:
                # --- Active with 2 attempts (warning zone) ---
                for j in range(2):
                    ContactAttempt.objects.create(
                        assignment=assignment,
                        attempted_by=volunteer,
                        method='phone' if j == 0 else 'email',
                        notes=CONTACT_NOTES_TEXTS[j],
                    )

            elif i < 20:
                # --- Active with 1 attempt ---
                ContactAttempt.objects.create(
                    assignment=assignment,
                    attempted_by=volunteer,
                    method='phone',
                    notes=CONTACT_NOTES_TEXTS[0],
                )

            # else: active with no attempts yet

        # Update goal progress to reflect actual data
        for vol in volunteers:
            completed = Assignment.objects.filter(volunteer=vol, status=Assignment.STATUS_COMPLETED).count()
            attempts  = ContactAttempt.objects.filter(attempted_by=vol).count()
            Goal.objects.filter(user=vol, title="Visit 10 Companies").update(current_value=completed)
            Goal.objects.filter(user=vol, title="Contact Attempts").update(current_value=attempts)

        counts = {
            "visited": Assignment.objects.filter(status="completed").count(),
            "lost":    Assignment.objects.filter(status="lost").count(),
            "active":  Assignment.objects.filter(status="active").count(),
        }
        self.stdout.write(
            f"  Assignments — {counts['visited']} visited, {counts['lost']} lost, {counts['active']} active"
        )
        self.stdout.write(self.style.SUCCESS("Done! Log in with any volunteer (password: edawn2024)"))
