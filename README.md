# Barangay Connect

A Django-based Barangay Management System with a mobile-friendly resident portal and a staff workspace. It supports resident records, five certificate flows, templates, approval and release workflow, notifications, QR verification, print-ready documents, exports, and activity logging.

## Features

- Resident registration, login, profile, photo, and resident number
- Barangay Clearance, Residency, Indigency, Good Moral, and Business Permit requests
- Staff approval, rejection, release, notes, reference number, and resident notifications
- Customizable certificate and Barangay ID template records in the Django admin
- QR-code public verification page and print-ready certificate
- Resident directory and configuration through Django admin
- CSV request report and office activity log
- Bootstrap 5 responsive interface designed for phones

## Install and run

1. Create a virtual environment and activate it.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`. The default `DB_ENGINE=sqlite` lets you try the system immediately.
4. For MySQL, create a database named `barangay_db`, set `DB_ENGINE=mysql`, and provide the database credentials in `.env`.
5. Create the database tables: `python manage.py migrate` (the initial migration is included).
6. Create an office administrator: `python manage.py createsuperuser`
7. Start the server: `python manage.py runserver`

Open `http://127.0.0.1:8000/`. Office staff use `/admin/` to manage residents, templates, branding, and staff users. Mark an office user as **Staff status** in Django admin to grant the office dashboard and approval tools.

## Template variables

Certificate template body text may use `{{ resident.full_name }}`, `{{ request.purpose }}`, and `{{ barangay.name }}`. Add a `BarangayProfile`, the certificate templates, and an active `IDTemplate` from `/admin/` before going live.

## Production checklist

- Replace the development secret key and set `DEBUG=False`.
- Set an explicit `ALLOWED_HOSTS` list and use HTTPS.
- Configure a real email provider for notifications.
- Back up MySQL regularly and restrict admin accounts.
- The included document view is print-ready and works in all browsers. To enable direct PDF download, install `WeasyPrint` separately after the main setup.
