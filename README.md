# ADUN Photo Archive — Final Year Project

A smart event photo archive for Admiralty University of Nigeria, built with
Flask. Admins create school events and upload photos (JPEG/PNG or camera RAW
files such as ORF/CR2/NEF, which are converted automatically). OpenCV detects
faces in each photo, and admins can tag the detected faces with student
names. Students browse the gallery, search photos by event or by their name,
and download them.

## Features

- Role-based access (admin / student) with bcrypt-hashed passwords
- Event management (create, delete)
- Photo upload with automatic RAW-to-JPEG conversion
- AI face detection (OpenCV Haar cascade) with per-face tagging
- Gallery with lightbox viewer, search and download

## Setup

1. Create and activate a virtual environment, then install dependencies:

   ```
   python -m venv venv
   venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```

2. Create the MySQL database:

   ```sql
   CREATE DATABASE school_photo_db;
   ```

3. Configure the app via environment variables (recommended) or edit
   `config.py`:

   - `SECRET_KEY` — any long random string
   - `DATABASE_URL` — e.g. `mysql+pymysql://user:password@localhost/school_photo_db`
     (a SQLite URL such as `sqlite:///local_dev.db` also works for quick
     local testing)

4. Run the app:

   ```
   python run.py
   ```

   Tables are created automatically on first start.

5. Create the first administrator account:

   ```
   flask --app run.py create-admin
   ```

   Regular users who sign up through the Register page get the
   `student` role.

## Project structure

```
run.py             Entry point
config.py          Configuration (reads environment variables)
app/
  __init__.py      App factory, extensions
  models.py        User, Event, Photo, FaceTag models
  routes.py        All views (auth, events, upload, gallery, search, tagging)
  ai.py            RAW conversion and face detection
templates/         Jinja2 templates
static/uploads/    Uploaded photos, annotated copies and face crops
```
