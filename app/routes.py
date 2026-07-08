import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app import db, bcrypt
from app.models import User, Event, Photo, FaceTag
from app.ai import detect_faces
from functools import wraps
from flask import abort



def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admins only.', 'danger')
            return redirect(url_for('main.student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

main = Blueprint('main', __name__)

@main.route('/')
def index():
    print("Homepage accessed")
    return render_template('index.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
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

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('main.register'))

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please login.', 'danger')
            return redirect(url_for('main.register'))

        # Hash password and save user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
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
        event_name = request.form.get('event_name')
        event_date = request.form.get('event_date')
        description = request.form.get('description')

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


@main.route('/delete_event/<int:event_id>')
@login_required
@admin_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted.', 'info')
    return redirect(url_for('main.events'))


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'orf', 'cr2', 'nef', 'arw', 'dng', 'rw2'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload():
    events = Event.query.order_by(Event.event_date.desc()).all()

    if request.method == 'POST':
        print("Received upload request")
        event_id = request.form.get('event_id')
        files = request.files.getlist('photos')
        print(f"Selected event ID: {event_id}")
        print(f"Number of files received: {len(files)}")

        if not event_id:
            flash('Please select an event.', 'danger')
            return redirect(url_for('main.upload'))

        uploaded_count = 0

        for file in files:
            if not file:
                continue

            if not allowed_file(file.filename):
                continue

            try:
                filename = secure_filename(file.filename)
                print(f"Processing file: {filename}")

                if not filename:
                    continue

                upload_folder = os.path.join(
                    current_app.static_folder, 'uploads')
                os.makedirs(upload_folder, exist_ok=True)

                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                print(f"Saved file to: {filepath}")

                # Convert RAW to JPEG if needed
                raw_extensions = ['orf', 'cr2', 'nef', 'arw', 'dng', 'rw2']
                file_ext = filename.rsplit('.', 1)[-1].lower()
                display_filename = filename

                print(f"File extension: {file_ext}")

                if file_ext in raw_extensions:
                    print(f"Converting RAW file: {filename}")
                    from app.ai import convert_raw_to_jpeg
                    converted_path = convert_raw_to_jpeg(filepath)
                    print(f"Converted file path: {converted_path}")
                    if converted_path:
                        display_filename = os.path.basename(converted_path)
                        print(f"Display filename after conversion: {display_filename}")

                    else:
                        print(f"Failed to convert RAW file: {filename}")
               
                display_filepath = os.path.join(
                    upload_folder, display_filename)
                print(f"Display file path: {display_filepath}")
                
            
                # Run face detection
                print(f"Running face detection on: {display_filepath}")
                face_count, face_coords = detect_faces(display_filepath)
                
                print(f"Face count: {face_count}")
                print(f"Face coords: {face_coords}")

                new_photo = Photo(
                    filename=display_filename,
                    event_id=event_id,
                    faces_detected=face_count
                )
                db.session.add(new_photo)
                db.session.commit()  # Commit to get the photo ID for FaceTag entries
                print(f"New photo added with ID: {new_photo.id}")

                # Save each face's coordinates to FaceTag table
                print(f"Saving {len(face_coords)} face tags for photo ID: {new_photo.id}")
                for (x, y, w, h) in face_coords:
                    print(f"Adding FaceTag: x={x}, y={y}, w={w}, h={h}")
                    face_tag = FaceTag(
                        photo_id=new_photo.id,
                        person_name=None,  # Placeholder for future tagging
                        x=x,
                        y=y,
                        width=w,
                        height=h
                    )
                    db.session.add(face_tag)
                    print(f"FaceTag added for photo ID: {new_photo.id} with coordinates: ({x}, {y}, {w}, {h})")

                db.session.commit()  # Commit all FaceTag entries
                print("All face tags committed to the database.")
                uploaded_count += 1

            except Exception as e:
                print(f"Error processing file: {e}")
                continue

        db.session.commit()

        if uploaded_count > 0:
            flash(f'{uploaded_count} photo(s) uploaded successfully!', 'success')
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
        keyword = request.form.get('keyword', '')
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
    from flask import send_from_directory
    photo = Photo.query.get_or_404(photo_id)
    return send_from_directory(
        os.path.join(current_app.static_folder, 'uploads'),
        photo.filename,
        as_attachment=True
    )

@main.route('/delete_photo/<int:photo_id>')
@login_required
@admin_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)

    # Delete face tags first
    FaceTag.query.filter_by(photo_id=photo_id).delete()

    # Delete file from uploads folder
    try:
        file_path = os.path.join(
            current_app.static_folder, 'uploads', photo.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")

    # Delete photo record
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
                tag = FaceTag.query.get(int(tag_id))
                if tag:
                    tag.person_name = name if name else None

        db.session.commit()
        flash('Names saved successfully!', 'success')
        return redirect(url_for('main.tag_faces', photo_id=photo_id))

    return render_template('tag_faces.html',
                           photo=photo,
                           face_tags=face_tags)

@main.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.student_dashboard'))
    return render_template('admin_dashboard.html')


@main.route('/student/dashboard')
@login_required
def student_dashboard():
    return render_template('student_dashboard.html')
   