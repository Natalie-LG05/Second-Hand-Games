const player = document.getElementById('player');
const canvas = document.getElementById('canvas');
const context = canvas.getContext('2d');
const captureButton = document.getElementById('capture-button');
const formCameraInput = document.querySelector('#camera-input-div #camera_input');

const constraints = {
    video: true,
};

captureButton.addEventListener('click', () => {
// Draw the video frame to the canvas.
    context.drawImage(player, 0, 0, canvas.width, canvas.height);
    const imageDataURL = canvas.toDataURL('image/png');
    formCameraInput.value = imageDataURL;
});

// Attach the video stream to the video element and autoplay.
navigator.mediaDevices.getUserMedia(constraints).then((stream) => {
    player.srcObject = stream;
});