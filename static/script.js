const connections = [
    [0, 1], [1, 2], [2, 3], [3, 7],     // Right arm
    [0, 4], [4, 5], [5, 6], [6, 8],     // Left arm
    [9, 10],                           // Shoulders
    [11, 12], [11, 13], [13, 15],      // Left leg
    [12, 14], [14, 16],                // Right leg
    [11, 23], [12, 24],                // Torso to hips
    [23, 24], [23, 25], [25, 27],      // Left lower body
    [24, 26], [26, 28],                // Right lower body
    [27, 29], [29, 31],                // Left foot
    [28, 30], [30, 32],                // Right foot
];


const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const socket = io();

let webcamStream = null;
// Get webcam
navigator.mediaDevices.getUserMedia({ video: true }).then((stream) => {
    webcamStream = stream;
    video.srcObject = stream;
    video.play();
    processFrame();
});

const disconnectBtn = document.getElementById('disconnect-btn');
disconnectBtn.addEventListener('click', () => {
    console.log('Disconnect click')
    socket.disconnect();
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
    }
    window.location.replace('/');
});

// Send frames at ~15 FPS
function processFrame() {
    const hiddenCanvas = document.createElement('canvas');
    hiddenCanvas.width = video.videoWidth;
    hiddenCanvas.height = video.videoHeight;
    const hiddenCtx = hiddenCanvas.getContext('2d');
    hiddenCtx.drawImage(video, 0, 0, hiddenCanvas.width, hiddenCanvas.height);
    const imageData = hiddenCanvas.toDataURL('image/jpeg');
    socket.emit('frame', imageData);
    setTimeout(processFrame, 66); // ~15 fps
}

const similarityElem = document.getElementById("similarity");
// Draw landmarks
socket.on('landmarks', (landmarks) => {
    ctx.save();
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    drawPose(landmarks.live, 'red');
    drawPose(landmarks.target, 'blue');
    ctx.restore();
    similarityElem.innerText = `Similarity: ${landmarks.similarity}`;
});

function drawPose(landmarks, color) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    connections.forEach(([start, end]) => {
        const lmStart = landmarks[start];
        const lmEnd = landmarks[end];
        if (lmStart && lmEnd) {
            ctx.beginPath();
            ctx.moveTo(lmStart.x * canvas.width, lmStart.y * canvas.height);
            ctx.lineTo(lmEnd.x * canvas.width, lmEnd.y * canvas.height);
            ctx.stroke();
        }
    });
}
