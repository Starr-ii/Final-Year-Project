import glob
import os
from datetime import datetime
from functools import wraps

from flask import (Blueprint, render_template, redirect, url_for, request,
                   flash, current_app, send_from_directory)
from flask_login import (login_user, logout_user, login_required,
                         current_user)
from werkzeug.utils import secure_filename

from app import db, bcrypt
from app.models import User, Event, Photo, FaceTag
from app.ai import detect_faces, convert_raw_to_jpeg


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admins only.', 'danger')
            return redirect(url_for('main.student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'orf', 'cr2', 'nef', 'arw',
                      'dng', 'rw2'}
RAW_EXTENSIONS = {'orf', 'cr2', 'nef', 'arw', 'dng', 'rw2'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_folder():
    folder = os.path.join(current_app.static_folder, 'uploads')
    os.makedirs(folder, exist_ok=True)
    return folder


def unique_filename(folder, filename):
    """Return a filename whose base name (stem) is not used by any file in
    the folder yet. Uniqueness by stem matters because RAW files are later
    converted to <stem>.jpg and must not overwrite another photo."""
    base, ext = os.path.splitext(filename)
    candidate_base = base
    counter = 1
    while glob.glob(os.path.join(folder, glob.escape(candidate_base) + '.*')):
        candidate_base = f'{base}_{counter}'
        counter += 1
    return candidate_base + ext


def remove_photo_files(photo):
    """Delete every file belonging to a photo: the displayed image, the
    RAW original (if any), the annotated copy and the face crops."""
    folder = upload_folder()
    base = photo.filename.rsplit('.', 1)[0]
    targets = glob.glob(os.path.join(folder, glob.escape(base) + '.*'))
    targets += glob.glob(
        os.path.join(folder, 'processed_' + glob.escape(photo.filename)))
    targets += glob.glob(
        os.path.join(folder, 'faces', glob.escape(base) + '_face_*.jpg'))
    for path in targets:
        try:
            os.remove(path)
        except OSError as e:
            current_app.logger.warning('Could not delete %s: %s', path, e)


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('main.admin_dashboard'))
            else:
                return redirect(url_for('main.student_dashboard'))
        else:
            flash('Incorrect email or password.', 'danger')

    return render_template('login.html')


@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not full_name or not email or not password:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('main.register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('main.register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('main.register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please login.', 'danger')
            return redirect(url_for('main.register'))

        hashed_password = bcrypt.generate_password_hash(
            password).decode('utf-8')
        new_user = User(
            full_name=full_name,
            email=email,
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html')


@main.route('/create_event', methods=['GET', 'POST'])
@login_required
@admin_required
def create_event():
    if request.method == 'POST':
        event_name = request.form.get('event_name', '').strip()
        date_str = request.form.get('event_date', '')
        description = request.form.get('description', '').strip()

        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Please provide a valid event date.', 'danger')
            return redirect(url_for('main.create_event'))

        if not event_name:
            flash('Please provide an event name.', 'danger')
            return redirect(url_for('main.create_event'))

        new_event = Event(
            event_name=event_name,
            event_date=event_date,
            description=description
        )
        db.session.add(new_event)
        db.session.commit()

        flash('Event created successfully!', 'success')
        return redirect(url_for('main.events'))

    return render_template('create_event.html')


@main.route('/events')
@login_required
def events():
    all_events = Event.query.order_by(Event.event_date.desc()).all()
    return render_template('events.html', events=all_events)


@main.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
@admin_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    for photo in event.photos:
        remove_photo_files(photo)
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted.', 'info')
    return redirect(url_for('main.events'))


@main.route('/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload():
    events = Event.query.order_by(Event.event_date.desc()).all()

    if request.method == 'POST':
        event_id = request.form.get('event_id')
        files = request.files.getlist('photos')

        event = db.session.get(Event, int(event_id)) if event_id else None
        if event is None:
            flash('Please select a valid event.', 'danger')
            return redirect(url_for('main.upload'))

        uploaded_count = 0

        for file in files:
            if not file or not allowed_file(file.filename):
                continue

            filepath = None
            try:
                filename = secure_filename(file.filename)
                if not filename:
                    continue

                folder = upload_folder()
                filename = unique_filename(folder, filename)
                filepath = os.path.join(folder, filename)
                file.save(filepath)

                # Convert RAW to JPEG if needed
                file_ext = filename.rsplit('.', 1)[-1].lower()
                display_filename = filename

                if file_ext in RAW_EXTENSIONS:
                    converted_path = convert_raw_to_jpeg(filepath)
                    if converted_path:
                        display_filename = os.path.basename(converted_path)
                    else:
                        current_app.logger.error(
                            'Failed to convert RAW file: %s', filename)
                        continue

                display_filepath = os.path.join(folder, display_filename)

                face_count, face_coords = detect_faces(display_filepath)

                new_photo = Photo(
                    filename=display_filename,
                    event_id=event.id,
                    faces_detected=face_count
                )
                db.session.add(new_photo)
                db.session.flush()  # Assigns the photo ID for FaceTag rows

                for (x, y, w, h) in face_coords:
                    db.session.add(FaceTag(
                        photo_id=new_photo.id,
                        person_name=None,
                        x=x,
                        y=y,
                        width=w,
                        height=h
                    ))

                db.session.commit()
                uploaded_count += 1

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(
                    'Error processing file %s: %s', file.filename, e)
                # Don't leave a half-processed file behind
                if filepath and os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass
                continue

        if uploaded_count > 0:
            flash(f'{uploaded_count} photo(s) uploaded successfully!',
                  'success')
        else:
            flash('No valid photos were uploaded.', 'danger')

        return redirect(url_for('main.gallery'))

    return render_template('upload.html', events=events)


@main.route('/gallery')
@login_required
def gallery():
    all_photos = Photo.query.join(Event).order_by(
        Event.event_name.asc(),
        Photo.upload_date.desc()
    ).all()
    return render_template('gallery.html', photos=all_photos)


@main.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    events = Event.query.order_by(Event.event_name.asc()).all()
    results = []
    keyword = ''
    selected_event = ''
    searched = False

    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        selected_event = request.form.get('event_id', '')
        searched = True

        # Search by event name OR person name
        query = Photo.query.join(Event)

        if keyword:
            # Find photos where event name matches
            # OR where a tagged person's name matches
            matching_photo_ids = db.session.query(FaceTag.photo_id).filter(
                FaceTag.person_name.ilike(f'%{keyword}%')
            ).distinct()

            query = query.filter(
                db.or_(
                    Event.event_name.ilike(f'%{keyword}%'),
                    Photo.id.in_(matching_photo_ids)
                )
            )

        if selected_event:
            query = query.filter(Photo.event_id == selected_event)

        results = query.order_by(Photo.upload_date.desc()).all()

    return render_template('search.html',
        events=events,
        results=results,
        keyword=keyword,
        selected_event=selected_event,
        searched=searched
    )


@main.route('/download/<int:photo_id>')
@login_required
def download(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    return send_from_directory(
        upload_folder(),
        photo.filename,
        as_attachment=True
    )


@main.route('/delete_photo/<int:photo_id>', methods=['POST'])
@login_required
@admin_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)

    remove_photo_files(photo)

    # Face tags are removed automatically via the relationship cascade
    db.session.delete(photo)
    db.session.commit()

    flash('Photo deleted successfully.', 'info')
    return redirect(url_for('main.gallery'))


@main.route('/tag_faces/<int:photo_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def tag_faces(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    face_tags = FaceTag.query.filter_by(photo_id=photo_id).all()

    if request.method == 'POST':
        total_tags = int(request.form.get('total_tags', 0))

        for i in range(total_tags):
            tag_id = request.form.get(f'tag_id_{i}')
            name = request.form.get(f'name_{tag_id}', '').strip()

            if tag_id:
                tag = db.session.get(FaceTag, int(tag_id))
                if tag and tag.photo_id == photo.id:
                    tag.person_name = name if name else None

        db.session.commit()
        flash('Names saved successfully!', 'success')
        return redirect(url_for('main.tag_faces', photo_id=photo_id))

    return render_template('tag_faces.html',
                           photo=photo,
                           face_tags=face_tags)


@main.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')


@main.route('/student/dashboard')
@login_required
def student_dashboard():
    return render_template('student_dashboard.html')
