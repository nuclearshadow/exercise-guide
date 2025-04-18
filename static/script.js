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

// Draw landmarks
socket.on('landmarks', (landmarks) => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    landmarks.forEach(lm => {
        ctx.beginPath();
        ctx.arc(lm.x * canvas.width, lm.y * canvas.height, 5, 0, 2 * Math.PI);
        ctx.fillStyle = 'red';
        ctx.fill();
    });
});
