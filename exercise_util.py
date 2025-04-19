import os
import cv2
import json
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# === CONFIG ===
IMAGE_DIR = 'assets/poses/body_weight_squat'  # directory with key pose images
OUTPUT_JSON = 'exercises/body_weight_squat.json'
MODEL_PATH = 'assets/pose_landmarker_lite.task'

# === MediaPipe Setup ===
BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE
)
landmarker = PoseLandmarker.create_from_options(options)

# === Process Images ===
key_poses = []

for fname in sorted(os.listdir(IMAGE_DIR)):
    if not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue

    path = os.path.join(IMAGE_DIR, fname)
    img = cv2.imread(path)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)

    result = landmarker.detect(mp_image)

    if not result.pose_landmarks or len(result.pose_landmarks[0]) == 0:
        print(f"⚠️ No landmarks found in {fname}")
        continue

    pose_landmarks = [
        {
            "x": lm.x,
            "y": lm.y,
            "z": lm.z,
            "visibility": lm.visibility
        }
        for lm in result.pose_landmarks[0]
    ]

    pose_world_landmarks = [
        {
            "x": lm.x,
            "y": lm.y,
            "z": lm.z,
            "visibility": lm.visibility
        }
        for lm in result.pose_world_landmarks[0]
    ]

    key_poses.append({
        "pose_landmarks": pose_landmarks,
        "pose_world_landmarks": pose_world_landmarks
    })

# === Write to JSON ===
os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
with open(OUTPUT_JSON, 'w') as f:
    json.dump({
        "key_poses": key_poses
    }, f, indent=2)

landmarker.close()
print(f"✅ Saved {len(key_poses)} key poses to {OUTPUT_JSON}")
