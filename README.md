# Coderr Backend

Backend for a freelancer developer platform.  
Built with **Django** and **Django REST Framework (DRF)**.

---

## Coderr Backend

Coderr is the backend for a freelance developer marketplace built with Django and Django REST Framework (DRF). This repository contains the API, models and admin configuration required to manage users, profiles, offers, orders and reviews.

This README documents how to set up the development environment, run the project, run tests and summarizes the main API endpoints and special project behaviours.

## Table of Contents

- Requirements
- Quick start (development)
- Environment & configuration
- Database and migrations
- Media files
- API overview (authentication, profiles, offers, orders, reviews)
- Admin
- Tests
- Notes & special behaviors
- Contributing

## Requirements

- Python 3.11 or newer
- See `requirements.txt` for pinned dependencies (Django 5.2.5, djangorestframework, django-filter, pillow, etc.)

Installable dependencies are included in `requirements.txt`.

## Quick start (development)

1. Clone the repo and change into the project directory:

   git clone <repo-url>
   cd Coderr-backend

2. Create and activate a virtual environment (Windows PowerShell example):

   python -m venv env; .\env\Scripts\Activate.ps1

3. Install dependencies:

   pip install -r requirements.txt

4. Apply migrations and create a superuser:

   python manage.py migrate
   python manage.py createsuperuser

5. (Optional) Collect static files if serving static assets differently:

   python manage.py collectstatic --noinput

6. Run the development server:

   python manage.py runserver

The API root is mounted under `/api/`. The Django admin is available at `/admin/`.

## Environment & configuration

- Settings live in `core/settings.py`.
- By default `DEBUG = True` and the project uses a local SQLite database at `PostgreSQL`.
- Media files are stored in the `media/` directory (see `MEDIA_ROOT` and `MEDIA_URL` in settings).
- The project uses TokenAuthentication from DRF for API authentication.
- Rate limiting (throttling) is configured in `REST_FRAMEWORK` settings. Default throttle rates and classes are defined there.

For production use you must:
- Replace the hard-coded `SECRET_KEY` with a secure one (do not commit it into the repo).
- Set `DEBUG = False`.
- Configure `ALLOWED_HOSTS` and a production-ready database (Postgres, etc.).
- Properly configure static/media file serving and HTTPS.

## Database and migrations

- Migrations are stored in each app's `migrations/` folder. To apply migrations locally run:

  python manage.py migrate

- If you add models, create migrations with:

  python manage.py makemigrations

## Media files

- Uploaded files are saved under the `media/` directory. `MEDIA_URL` is `/media/` and `MEDIA_ROOT` points to `media/` in the project root.
- Offers upload files into `media/offers/`. Profile uploads go into `media/profile/`.

When running locally Django will serve media files automatically via the `static()` helper included in `core/urls.py`.

## API overview

General notes
- The API root is at `/api/`.
- Authentication: DRF Token Authentication. Endpoints are protected by default (`IsAuthenticated` is the default permission class) unless a view explicitly allows anonymous access.
- Use the Authorization header for requests that require authentication:

  Authorization: Token <your-token>

### Authentication & user management

- POST `/api/registration/` — Create a new user and profile.
  - Required fields: `username`, `email`, `password`, `repeated_password`, `type` ("customer" or "business").
  - Passwords must match. Email uniqueness is enforced.

- POST `/api/login/` — Obtain an authentication token.

### Profiles

- GET / PATCH `/api/profile/{pk}/` — Retrieve and update a profile.
  - Profiles expose fields: `user`, `username`, `first_name`, `last_name`, `file`, `location`, `tel`, `description`, `working_hours`, `type`, `email`, `created_at`.
  - The API returns empty/blank values as an empty string `""` (not `null`).
  - File upload for profiles is supported. When a file is uploaded the `uploaded_at` timestamp is set automatically.

- GET `/api/profiles/business/` — List business profiles (limited fields appropriate for businesses).
- GET `/api/profiles/customer/` — List customer profiles (includes `uploaded_at`).

### Offers

Offers model: each `Offer` has an optional image and three nested `OfferDetail` entries (basic, standard, premium).

- GET `/api/offers/` — List offers (paginated). Supports filters:
  - `creator_id` — filter by offer creator id
  - `min_price` — filter by minimal price
  - `max_delivery_time` — filter by max delivery time in days
  - `ordering` — e.g. `updated_at`, `min_price`
  - `search` — searches `title` and `description`

- POST `/api/offers/` — Create a new offer (must be a business user).
  - When creating an offer you MUST provide exactly 3 `details` objects: one each for `offer_type` = `basic`, `standard`, `premium`. Each detail requires fields: `title`, `revisions`, `delivery_time_in_days`, `price`, `features` (non-empty list), `offer_type`.

- GET `/api/offers/{id}/` — Retrieve one offer with nested details and aggregated fields like `min_price` and `min_delivery_time`.
- PATCH `/api/offers/{id}/` — Update offer or existing details (only owner allowed). When updating details, `offer_type` is used to match which detail to update; duplicate `offer_type` values are rejected.
- DELETE `/api/offers/{id}/` — Delete an offer (only owner allowed).

- GET `/api/offerdetails/{id}/` — Retrieve a single `OfferDetail` resource (requires authentication).

### Orders

- Orders are placed by customers for a specific `OfferDetail` and reference both `customer_user` and `business_user`.
- POST, GET and PATCH endpoints for `orders` are available via the router at `/api/orders/` (the router is registered in `coderr_app.api.urls`).
- There are helper endpoints to get order counts for a business user:
  - `GET /api/order-count/{business_user_id}/` — counts in-progress orders
  - `GET /api/completed-order-count/{business_user_id}/` — counts completed orders

### Reviews

- Reviews allow authenticated users to leave a rating (1–5) and a description for a `business_user`.
- A user can only review a given business once. The API enforces that `business_user` must be a user with a `Profile` of type `business`.

## Admin

- The Django admin is available at `/admin/` and can manage `User`, `Profile`, `Offer`, `OfferDetail`, `Order`, `Review`.

Create a superuser with:

  python manage.py createsuperuser

## Tests

- The project contains unit and API tests under each app's `tests/` directory. Run tests with:

  python manage.py test

The existing tests claim very high coverage; ensure you run them in an up-to-date virtual environment.

## Notes & special behaviors

- Profiles return blank strings for empty fields instead of `null` for easier client handling.
- Creating an `Offer` requires exactly three `OfferDetail` objects (one for each `offer_type`). The serializer enforces uniqueness of `offer_type` values and exact presence of the three types on create.
- File fields are handled with care: updating profile file to an empty value deletes the stored file and clears `uploaded_at`.
- Authentication is required for most endpoints; only registration and login are anonymous.
- Default throttling settings exist for anonymous and authenticated users; there are custom throttle keys for registration and login actions.

## Contributing

- Fork the repository, create a feature branch, add tests for new behavior, and submit a pull request.
- Keep code PEP8 compliant. The project follows DRF best practices.

## Troubleshooting

- If you see permission errors on API endpoints, ensure you include the token header and that the token belongs to a user with the correct `Profile.type` (e.g. business for posting offers).
- If media files are not served in production, configure a proper media/static hosting solution (S3, CDN or a web server) and update `MEDIA_URL`/`MEDIA_ROOT` accordingly.

## Contact

If you need help with this repository, open an issue describing the problem and include Django version, Python version, and a short error trace where applicable.
