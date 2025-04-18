from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import cv2
import base64
import numpy as np
import mediapipe as mp
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

model_path = 'assets/pose_landmarker_lite.task'

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
PoseLandmarkerResult = mp.tasks.vision.PoseLandmarkerResult
VisionRunningMode = mp.tasks.vision.RunningMode

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.VIDEO)

landmarker = PoseLandmarker.create_from_options(options) 

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/session')
def session():
    return render_template('session.html')

@socketio.on('frame')
def handle_frame(data):
    image_data = data.split(',')[1]
    img_bytes = base64.b64decode(image_data)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    if np_arr.size <= 0: 
        print('Empty array')
        return
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)

    # Process with MediaPipe
    result = landmarker.detect_for_video(mp_image, time.time_ns()//1_000_000)
    landmarks = []
    if len(result.pose_landmarks) > 0:
        for lm in result.pose_landmarks[0]:
            landmarks.append({
                'x': lm.x,
                'y': lm.y,
                'z': lm.z,
                'visibility': lm.visibility
            })

    emit('landmarks', landmarks)
    

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
    landmarker.close()
