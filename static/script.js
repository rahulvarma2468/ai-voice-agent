// --- Session ID Handling --- //
let sessionId;
(function getSessionId() {
    const params = new URLSearchParams(window.location.search);
    let sid = params.get('session');
    if (!sid) {
        sid = Math.random().toString(36).substring(2, 12);
        params.set('session', sid);
        window.history.replaceState({}, "", `${location.pathname}?${params.toString()}`);
    }
    sessionId = sid;
})();

// --- UI Element references --- //
const statusEl = document.getElementById('status');
const recordBtn = document.getElementById('record-btn');

// --- Status Message Helper --- //
function setStatus(message, isError = false) {
    statusEl.textContent = message;
    statusEl.className = `status visible ${isError ? 'error' : 'success'}`;
    setTimeout(() => {
        statusEl.classList.remove('visible');
    }, 4000);
}

// --- Recording/WebSocket State --- //
let mediaRecorder = null;
let ws = null;
let isRecording = false;

// --- Start/Stop Button Handler --- //
function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

// --- Start Audio Streaming --- //
function startAudioStream() {
    ws = new WebSocket("ws://localhost:8000/ws/audio");

    ws.onopen = () => {
        setStatus("🎤 Streaming audio...");
        console.log("WebSocket opened");
    };

    ws.onerror = () => {
        setStatus("WebSocket error!", true);
        console.error("WebSocket error");
    };

    ws.onclose = () => {
        setStatus("Audio stream closed.");
        console.log("WebSocket closed");
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
        }
        isRecording = false;
        updateRecordBtn(false);
    };
}

// --- Send Each Audio Chunk over WebSocket --- //
function sendAudioChunk(audioChunk) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        audioChunk.arrayBuffer().then(buffer => {
            try {
                ws.send(buffer);
            } catch (err) {
                console.error("WebSocket send failed:", err);
            }
        });
    }
}

// --- Start Recording --- //
function startRecording() {
    if (!navigator.mediaDevices) {
        setStatus("Browser doesn't support recording.", true);
        return;
    }
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            startAudioStream();
            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = function(e) {
                if (e.data.size > 0) sendAudioChunk(e.data);
            };

            mediaRecorder.onstop = function() {
                setStatus("Recording stopped.");
                if (ws && ws.readyState === WebSocket.OPEN) ws.close();
            };

            mediaRecorder.start(200); // Send chunk every 200ms
            isRecording = true;
            updateRecordBtn(true);
            setStatus("Recording started...", false);
            console.log("Recording started");
        })
        .catch(() => setStatus("Microphone access denied.", true));
}

// --- Stop Recording --- //
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        setStatus("Processing...", false);
        console.log("Recording stopped");
    }
}

// --- Update Record Button UI --- //
function updateRecordBtn(recording) {
    if (recording) {
        recordBtn.textContent = "⏹ Stop";
        recordBtn.classList.add('recording');
        recordBtn.setAttribute('aria-pressed', 'true');
        recordBtn.setAttribute('aria-label', 'Stop recording');
    } else {
        recordBtn.textContent = "🎤 Start";
        recordBtn.classList.remove('recording');
        recordBtn.setAttribute('aria-pressed', 'false');
        recordBtn.setAttribute('aria-label', 'Start recording');
    }
}

// --- Attach to button --- //
recordBtn.onclick = toggleRecording;
