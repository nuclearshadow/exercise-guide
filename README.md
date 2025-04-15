# Exercise Guide

A real-time exercise guide application that uses computer vision to track poses and provide feedback. The application allows you to record exercise templates and compare your current pose with the recorded template.

## Features

- Real-time pose tracking using MediaPipe
- Exercise template recording and playback
- Pose similarity scoring
- Real-time feedback on form
- Web-based interface with live video feed

## Prerequisites

- Python 3.8 or higher
- Webcam
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd exercise-guide
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5001
```

## Using the Application

TBD