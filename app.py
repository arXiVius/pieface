# app.py

import os
from flask import Flask, render_template, redirect, url_for, request, flash, Response, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import User, Presence
from database import db
import cv2
import numpy as np
import face_recognition

# --- THE FIX STARTS HERE: Make sure PIL is imported ---
from PIL import Image 

# --- App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-super-secret-key' # This should be a real secret
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'

# --- Database and Login Manager Initialization ---
db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# New, correct version
@login_manager.user_loader
def load_user(user_id):
 return db.session.get(User, int(user_id))

# --- OpenCV Globals for Camera Feed ---
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
camera = None

def get_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
    return camera

def release_camera():
    global camera
    if camera:
        camera.release()
        camera = None

# --- THE DEFINITIVE FIX: Replace the old get_face_encoding with this one ---
def get_face_encoding(image_stream):
    """
    Loads an image stream using OpenCV, converts it to RGB, 
    and returns the 128-d face encoding.
    """
    try:
        # Step 1: Read the stream into a NumPy array
        filestr = image_stream.read()
        npimg = np.frombuffer(filestr, np.uint8)
        
        # Step 2: Decode the array into an image using OpenCV
        image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        
        # Step 3: CRITICAL Conversion from BGR (OpenCV default) to RGB (face_recognition requirement)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Step 4: Get the face encodings from the RGB image
        face_encodings = face_recognition.face_encodings(image_rgb)
        
        if len(face_encodings) == 1:
            return face_encodings[0]
        else:
            print(f"Found {len(face_encodings)} faces in the image. Expected 1.")
            return None
            
    except Exception as e:
        print(f"An error occurred in get_face_encoding: {e}")
        return None

# --- Video Streaming Generator (Unchanged) ---
def generate_frames():
    cam = get_camera()
    while True:
        success, frame = cam.read()
        if not success:
            break
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    release_camera()

# --- ROUTES (Unchanged from face_recognition version) ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        file = request.files.get('face_image')

        if not file or file.filename == '':
            flash('Face image is required.')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))

        encoding = get_face_encoding(file.stream)
        if encoding is None:
            flash('No unique face detected. Please use a clear, front-facing photo.')
            return redirect(url_for('register'))
        
        encoding_str = ','.join(map(str, encoding))

        new_user = User(username=username, face_encoding=encoding_str)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('Please check your login details and try again.')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    release_camera()
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    presence_records = Presence.query.filter_by(user_id=current_user.id).order_by(Presence.timestamp.desc()).paginate(page=page, per_page=10)
    return render_template('dashboard.html', name=current_user.username, records=presence_records.items, pagination=presence_records)

@app.route('/video_feed')
@login_required
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/mark_presence', methods=['POST'])
@login_required
def mark_presence():
    file = request.files.get('presence_capture')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')

    if not file:
        return jsonify({'status': 'error', 'message': 'Capture data not received.'}), 400

    stored_encoding_str = current_user.face_encoding
    if not stored_encoding_str:
        return jsonify({'status': 'error', 'message': 'Error: No face encoding found for this user.'}), 400

    stored_encoding = np.array([float(num) for num in stored_encoding_str.split(',')])
    
    new_encoding = get_face_encoding(file.stream)
    
    if new_encoding is None:
        return jsonify({'status': 'error', 'message': 'No face detected in the captured image.'}), 400

    distance = face_recognition.face_distance([stored_encoding], new_encoding)[0]
    
    is_match = distance < 0.6
    status = 'Verified' if is_match else 'Unverified'

    presence = Presence(
        user_id=current_user.id,
        latitude=latitude,
        longitude=longitude,
        status=f"{status} (Distance: {distance:.2f})"
    )
    db.session.add(presence)
    db.session.commit()

    # Prepare the record data for the frontend
    record_data = {
        'timestamp': presence.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'status': presence.status,
        'lat': float(presence.latitude) if presence.latitude else 'N/A',
        'long': float(presence.longitude) if presence.longitude else 'N/A'
    }

    return jsonify({'status': 'success', 'message': f'Presence marked as {status}.', 'record': record_data})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)