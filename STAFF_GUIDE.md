# EDAWN Business Builders Portal — Staff Guide

**For:** Kim Yaeger, EDAWN Staff Administrator  
**Last updated:** May 2026

---

## Table of Contents

1. [Signing In](#1-signing-in)
2. [Staff Dashboard](#2-staff-dashboard)
3. [Managing Volunteers](#3-managing-volunteers)
4. [Adding and Importing Companies](#4-adding-and-importing-companies)
5. [Assigning Companies](#5-assigning-companies)
6. [Assignment Requests](#6-assignment-requests)
7. [Messaging Volunteers](#7-messaging-volunteers)
8. [Dashboard Notices](#8-dashboard-notices)
9. [Resource Library](#9-resource-library)
10. [Exporting Visit Data](#10-exporting-visit-data)
11. [Expansion Signals](#11-expansion-signals)
12. [Quick Reference](#12-quick-reference)

---

## 1. Signing In

Go to the portal URL and sign in with your staff username and password. Because your account has staff permissions, you will see the regular volunteer navigation on the left **plus** a Staff section below it.

If you ever forget your password, contact your system administrator to reset it.

---

## 2. Staff Dashboard

The Staff Dashboard is your home base. Reach it by clicking **Staff Dashboard** in the left sidebar.

### Stat Cards

The row of cards at the top gives you a live count of:

| Card | What it means |
|---|---|
| **Total Companies** | Every company in the system |
| **Unassigned** | Companies with no volunteer assigned |
| **Active** | Companies currently being worked by a volunteer |
| **Visited** | Companies that have received a completed visit |
| **Unvisited 60+ Days** | Active assignments with no visit logged in over 60 days |
| **Overdue Volunteers** | Volunteers with an active assignment but no visit in 45+ days |
| **BBV Overdue** | Volunteers who have been active 90+ days without earning BBV certification |
| **Pending Requests** | Volunteer requests awaiting your approval |

Cards with a colored border need attention. Click the **Pending Requests** or **BBV Overdue** cards to jump straight to the relevant list.

### Quick Actions

The Quick Actions bar gives you one-click access to the most common tasks: adding a company, importing a CSV, assigning a company, and more.

### Recent Assignments

The lower section shows the 10 most recent assignments so you can see what's been active lately.

---

## 3. Managing Volunteers

Go to **Staff → Volunteer Roster** in the sidebar.

### Understanding the Roster

Each row shows a volunteer's name, email, assignment counts, last visit date, current status badge, and whether they've completed training and BBV certification.

**Status badges:**
- **Active** — has an active assignment and is within the 45-day visit window
- **Overdue** — has an active assignment but hasn't logged a visit in 45+ days
- **No Active** — no current assignment (has done work before)
- **Unassigned** — brand new, never had an assignment
- **BBV Overdue** — eligible for BBV certification but hasn't been certified yet

### Filter Tabs

Use the filter buttons at the top to narrow the list:
- **Overdue** — shows only volunteers who need a check-in
- **No Assignments** — useful for finding inactive volunteers to re-engage
- **BBV Overdue** — volunteers ready for certification review

### Marking Training Complete

When a volunteer completes their onboarding session, click **Mark Done** in their Training column. The button turns green and shows the completion date. Click it again to undo if needed.

### Granting BBV Certification

When a volunteer has visited companies in three consecutive calendar months, click **Grant BBV** in their BBV column. This unlocks their ability to hold more than one active assignment at a time. Click the blue **Certified** button to revoke if needed.

### Resetting a Volunteer's Password

If a volunteer is locked out, click the small **Temp Password** button under their email address. Confirm the prompt and a new 10-character password will appear in a green banner at the top of the page. Read it to the volunteer over the phone or email it to them directly and ask them to change it after signing in (they can do this under **Change Password** in the sidebar).

### Inviting a New Volunteer

Go to **Staff → Invite Volunteer**. Enter the new volunteer's name and email, then click **Generate Link**. This creates a single-use registration link pre-filled with an invite code. Copy the link and send it to the volunteer — when they click it, they land on the registration page with their invite code already filled in.

---

## 4. Adding and Importing Companies

### Adding a Single Company

Click **Add Company** from the Quick Actions bar or the Staff Dashboard. Fill in the company name, industry, address, and any contact information you have. Click **Save**.

### Importing from CSV

For bulk uploads, use **Import CSV** from the Quick Actions bar.

**Preparing your file:**
- Save the spreadsheet as a `.csv` file
- The importer recognises these column names (case-insensitive, spaces or underscores):

| Field | Example column names accepted |
|---|---|
| Company name | `name`, `company`, `company name` |
| Industry | `industry`, `industry group` |
| Address | `address`, `street`, `street address` |
| City | `city` |
| State | `state` |
| Zip | `zip`, `zip code`, `postal code` |
| Phone | `phone`, `phone number` |
| Email | `email` |
| Website | `website`, `url` |
| Contact name | `contact`, `contact name`, `primary contact` |

- Columns that don't match any of the above are safely ignored
- Companies that already exist (matched by name) are updated, not duplicated

Upload the file, review the preview, and click **Import**.

---

## 5. Assigning Companies

### Quick Assign

Click **Assign Company** from the Quick Actions bar or sidebar.

1. Choose a company from the dropdown (companies are grouped by industry, and only unassigned companies appear)
2. Choose a volunteer
3. Click **Assign**

The company status changes to **Active** and it immediately appears on the volunteer's dashboard.

**BBV rule:** Non-certified volunteers can only hold one active assignment at a time. The system will warn you if you try to assign a second company to a non-BBV volunteer.

### Assigning from a Browse Request

When a volunteer requests a company (see Section 6), you can approve it directly from the **Requests** page rather than using Quick Assign.

---

## 6. Assignment Requests

Volunteers can browse unassigned companies and submit requests to be assigned. Go to **Staff → Requests** to manage these.

### Pending Requests

The top of the page lists all pending requests grouped by company. You can see how many volunteers have requested the same company.

- Click **Approve** to assign the company to that volunteer. All other pending requests for the same company are automatically denied.
- Click **Deny** to decline the request without assigning anyone.

When you approve a request, the system checks the BBV cap automatically — if the volunteer already has an active assignment and isn't BBV certified, it will block the approval and show a warning.

### Recent Activity

Below the pending list you'll see the last 20 approved/denied requests for reference.

---

## 7. Messaging Volunteers

Go to **Messages → New** in the sidebar (or click the **New** button on the Messages page).

### Message Types (Staff Only)

When you're composing a message, you'll see a **Send To** tab strip:

| Tab | Who receives it |
|---|---|
| **All Volunteers** | Every active volunteer in the system |
| **By Industry** | Volunteers who have an assignment in a specific industry |
| **Direct Message** | One specific volunteer |
| **Staff Board** | Posts to the group board visible to all (same as what volunteers see) |

Messages show up in the recipient's Messages page. Direct messages are private — only the recipient and staff can see them.

### Replies

Anyone who can see a message can add a reply. Threads stay together on the message detail page.

---

## 8. Dashboard Notices

Notices are banner announcements that appear at the top of every volunteer's dashboard. Use them for event reminders, program updates, or anything time-sensitive.

Go to **Staff → Notices**.

### Creating a Notice

Click **New Notice** and fill in:

- **Title** — the bold headline volunteers see (required)
- **Details** — optional body text below the title
- **Expiry date/time** — required; the notice disappears automatically after this point
- **Link URL / Link text** — optional; adds a button to the notice (e.g. a sign-up link)
- **Active** — uncheck to hide a notice without deleting it

### Managing Existing Notices

The notices list shows each notice's current status:
- **Live** (green) — active and not yet expired, visible to volunteers now
- **Off** (grey) — manually deactivated
- **Expired** (yellow) — past the expiry date, no longer showing

Click the pencil icon to edit or the trash icon to delete.

---

## 9. Resource Library

The Resources page is where you publish links to documents, guides, and tools for volunteers. Go to **Resources** in the sidebar.

### Adding a Resource

Click **Add Resource** (visible only to you as staff).

- **Title** — what volunteers see (e.g. "Visit Script — Manufacturing")
- **Description** — optional short explanation
- **Category** — choose from: Visit Script, Company Snapshot Form, Workforce Guide, EDAWN Value Prop, or Other
- **URL** — paste your OneDrive sharing link
- **Sort order** — lower numbers appear first within their category (default 0)
- **Active** — uncheck to hide without deleting

### Editing and Hiding Resources

Click the pencil icon next to any resource. Hidden (inactive) resources appear dimmed for you but are invisible to volunteers. Use this to temporarily pull a resource without losing the link.

---

## 10. Exporting Visit Data

Go to **Staff → Export Data**.

Use the filters to narrow what you export:

- **Date range** — visits between two dates
- **Industry** — filter to one industry
- **Volunteer** — filter to one volunteer

Leave filters blank to export everything. Click **Export CSV** and the file downloads immediately.

The CSV includes: company name, industry, city, volunteer name, visit date, hiring status, employee count, jobs added/lost, expansion flags, and follow-up notes.

---

## 11. Expansion Signals

Go to **Staff → Expansion Signals**.

This page surfaces companies whose most recent visit note indicated expansion activity — adding square footage, looking for a new building, adding equipment, or planning capital expenditure. It's a quick way to identify companies that may need follow-up from the EDAWN economic development team.

---

## 12. Quick Reference

### Key Rules to Know

| Rule | Detail |
|---|---|
| **Assignment cap (non-BBV)** | Volunteers without BBV certification can only hold 1 active assignment at a time |
| **Assignment cap (BBV)** | BBV-certified volunteers can hold unlimited active assignments |
| **Request cap** | Volunteers can have at most 3 pending requests at a time |
| **Overdue threshold** | A volunteer is flagged as Overdue after 45 days without a visit (new volunteers get a 45-day grace period from their first assignment) |
| **Unvisited 60+ days** | Companies with no visit logged in 60+ days appear on the dashboard warning card |
| **BBV eligibility** | A volunteer qualifies for BBV after completing visits in 3 consecutive calendar months |
| **BBV overdue** | Eligible volunteers not yet certified are flagged after 90 days of active participation |
| **Invite codes** | Registration links are single-use — generate a new one for each volunteer |
| **Notices** | Always set an expiry date; notices never disappear unless they expire or are manually deactivated |

### What Volunteers Can and Can't Do

Volunteers can:
- See and log contact attempts and visits for their assigned companies
- Browse unassigned companies and request assignment
- Message staff (directly) or post to the group board
- View their own badges and the leaderboard
- Access the resource library

Volunteers cannot:
- See other volunteers' direct messages
- Assign themselves a company without your approval
- See staff-only dashboard stats or the volunteer roster
- Export data

### Common Tasks — Where to Find Them

| Task | Where |
|---|---|
| Add a volunteer | Staff → Invite Volunteer |
| Reset a volunteer's password | Staff → Volunteer Roster → Temp Password button |
| Mark training complete | Staff → Volunteer Roster → Training column |
| Grant/revoke BBV | Staff → Volunteer Roster → BBV column |
| Add a company | Quick Actions → Add Company |
| Import companies | Quick Actions → Import CSV |
| Assign a company | Quick Actions → Assign Company |
| Review assignment requests | Staff → Requests (or click Pending Requests card on dashboard) |
| Post an announcement | Staff → Notices → New Notice |
| Message all volunteers | Messages → New → All Volunteers tab |
| Add a resource link | Resources → Add Resource |
| Export visit data | Staff → Export Data |
| See expansion signals | Staff → Expansion Signals |
