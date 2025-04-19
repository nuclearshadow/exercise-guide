from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import cv2
import base64
import numpy as np
import mediapipe as mp
import time
import os
import json
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

# === Global state ===
EXERCISES_PATH = 'exercises'
active_exercise = None
current_index = 0
reps = 0
SIMILARITY_THRESHOLD = 0.85

def reset_global_state():
    global active_exercise, current_index, reps
    active_exercise = None
    current_index = 0
    reps = 0

@app.route('/')
def index():
    exercises = []
    for f in os.listdir(EXERCISES_PATH):
        if f.endswith('.json'):
            raw = f.replace('.json', '')
            title = ' '.join(word.title() for word in raw.split('_'))
            exercises.append({'title': title, 'filename': raw})
    return render_template('index.html', exercises=exercises)

@app.route('/session/<exercise_name>')
def session(exercise_name):
    global active_exercise, current_index
    reset_global_state()
    path = os.path.join(EXERCISES_PATH, f'{exercise_name}.json')
    if not os.path.exists(path):
        return "Exercise not found", 404
    with open(path) as f:
        active_exercise = json.load(f)
    return render_template('session.html', exercise_name=exercise_name)

@socketio.on('frame')
def handle_frame(data):
    global current_index, reps
    if not active_exercise:
        return
    
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
    live_pose = []
    if len(result.pose_landmarks) > 0:
        for lm in result.pose_landmarks[0]:
            live_pose.append({
                'x': lm.x,
                'y': lm.y,
                'z': lm.z,
                'visibility': lm.visibility
            })
    
    user_in_frame = is_user_in_frame(live_pose)
    
    similarity = 0.0
    if len(result.pose_world_landmarks) > 0:
        user_world = result.pose_world_landmarks[0]
        target_world = active_exercise['key_poses'][current_index]['pose_world_landmarks']
        similarity = compare_poses(user_world, target_world)

        if similarity >= SIMILARITY_THRESHOLD:
            current_index += 1
            if current_index >= len(active_exercise['key_poses']):
                current_index = 0
                reps += 1
    
    # === Transform target pose landmarks to match user live pose ===
    transformed_target = transform_pose_to_match_user(
        active_exercise['key_poses'][current_index]['pose_landmarks'], live_pose
    )

    emit('landmarks', {
        'live': live_pose,
        'target': transformed_target,
        'similarity': similarity,
        'step': current_index,
        'reps': reps,
        'user_in_frame': user_in_frame,
    })



def is_user_in_frame(landmarks, visibility_threshold=0.5):
    if len(landmarks) == 0: return False
    def get_visibility(lm):
        return lm.visibility if hasattr(lm, 'visibility') else lm['visibility']

    return all(get_visibility(lm) > visibility_threshold for lm in landmarks)


def compare_poses(live, target):
    if not live or not target or len(live) != len(target):
        return 0.0

    def get_attr(lm, key):
        return getattr(lm, key) if hasattr(lm, key) else lm[key]

    total_distance = 0.0
    count = 0

    for lm1, lm2 in zip(live, target):
        v1 = get_attr(lm1, 'visibility')
        v2 = get_attr(lm2, 'visibility')

        # Skip if target doesn't care about this landmark
        if v2 <= 0.5:
            continue

        # If user landmark not visible, penalize with max distance
        if v1 <= 0.5:
            total_distance += 1.0  # max normalized distance
            count += 1
            continue

        x1, y1 = get_attr(lm1, 'x'), get_attr(lm1, 'y')
        x2, y2 = get_attr(lm2, 'x'), get_attr(lm2, 'y')

        dx = x1 - x2
        dy = y1 - y2
        dist = (dx**2 + dy**2) ** 0.5

        total_distance += dist
        count += 1

    if count == 0:
        return 0.0

    avg_dist = total_distance / count
    similarity = max(0.0, 1.0 - avg_dist * 2.0)

    return round(similarity, 3)


def transform_pose_to_match_user(target, user):
    if not target or not user:
        return target

    def average_point(p1, p2):
        return {
            'x': (p1['x'] + p2['x']) / 2,
            'y': (p1['y'] + p2['y']) / 2
        }

    def get_pose_metrics(pose):
        try:
            l_hip, r_hip = pose[23], pose[24]
            l_shoulder, r_shoulder = pose[11], pose[12]
        except IndexError:
            return {'x': 0.5, 'y': 0.5}, 1.0, 1.0  # defaults

        if any(p['visibility'] < 0.5 for p in [l_hip, r_hip, l_shoulder, r_shoulder]):
            return {'x': 0.5, 'y': 0.5}, 1.0, 1.0

        hip_center = average_point(l_hip, r_hip)
        shoulder_center = average_point(l_shoulder, r_shoulder)

        torso_height = ((hip_center['x'] - shoulder_center['x']) ** 2 +
                        (hip_center['y'] - shoulder_center['y']) ** 2) ** 0.5
        shoulder_width = ((l_shoulder['x'] - r_shoulder['x']) ** 2 +
                          (l_shoulder['y'] - r_shoulder['y']) ** 2) ** 0.5

        return hip_center, torso_height, shoulder_width

    # Extract metrics
    user_center, user_h_scale, user_w_scale = get_pose_metrics(user)
    target_center, target_h_scale, target_w_scale = get_pose_metrics(target)

    # Fallback to vertical scale if horizontal unreliable
    scale_y = user_h_scale / target_h_scale if target_h_scale else 1.0
    scale_x = (user_w_scale / target_w_scale) if target_w_scale > 0.05 else scale_y

    dx = user_center['x'] - target_center['x'] * scale_x
    dy = user_center['y'] - target_center['y'] * scale_y

    # Transform target
    aligned = []
    for lm in target:
        aligned.append({
            'x': lm['x'] * scale_x + dx,
            'y': lm['y'] * scale_y + dy,
            'z': lm['z'],  # untouched for now
            'visibility': lm['visibility']
        })

    return aligned


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
    landmarker.close()
