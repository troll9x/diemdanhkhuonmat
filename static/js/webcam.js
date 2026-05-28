const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
let recognizing = false;

navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => { video.srcObject = stream; });

async function sendFrame() {
    if (!recognizing) return;
    ctx.drawImage(video, 0, 0, 640, 480);

    canvas.toBlob(async (blob) => {
        const res = await fetch('/api/recognize/frame', {
            method: 'POST',
            headers: { 'Content-Type': 'image/jpeg' },
            body: blob
        });
        const data = await res.json();
        handleResult(data);
        setTimeout(sendFrame, 1500);  // send a frame every 1.5s
    }, 'image/jpeg', 0.8);
}

function handleResult(data) {
    const box = document.getElementById('result-box');
    if (data.status === 'success') {
        box.innerHTML = `✅ ${data.name} — ${data.department} (${data.confidence}%)`;
        box.className = 'alert alert-success';
    } else if (data.status === 'duplicate') {
        box.innerHTML = `⚠️ ${data.name} already marked today`;
        box.className = 'alert alert-warning';
    } else {
        box.innerHTML = `❌ Unknown face`;
        box.className = 'alert alert-danger';
    }
}