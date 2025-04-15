from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import cv2
import base64
import numpy as np
import mediapipe as mp

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=False)
mp_drawing = mp.solutions.drawing_utils

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('frame')
def handle_frame(data):
    image_data = data.split(',')[1]
    img_bytes = base64.b64decode(image_data)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Process with MediaPipe
    results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    landmarks = []
    if results.pose_landmarks:
        for lm in results.pose_landmarks.landmark:
            landmarks.append({
                'x': lm.x,
                'y': lm.y,
                'z': lm.z,
                'visibility': lm.visibility
            })

    emit('landmarks', landmarks)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
