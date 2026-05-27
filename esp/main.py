from machine import Pin
from time import sleep, ticks_ms, ticks_diff
import network
import socket
import os

try:
    import updater
except Exception as e:
    updater = None
    print("Updater not available:", e)


# ============================================================
# Konfiguration
# ============================================================

LED_PINS = [14, 27, 25, 32, 33]

UPDATE_INTERVAL_MS = 60_000

LOG_FILE = "recordings.csv"

# Fehlercode-Definitionen
# states: Grundzustand der LEDs
# blink_ms: 0 = kein Blinken, sonst Blinkintervall in Millisekunden
ERROR_CODES = {
    "fehlercode_01": {
        "description": "Alle LEDs aus",
        "states": [0, 0, 0, 0, 0],
        "blink_ms": [0, 0, 0, 0, 0]
    },
    "fehlercode_02": {
        "description": "LED 1 und LED 5 dauerhaft an",
        "states": [1, 0, 0, 0, 1],
        "blink_ms": [0, 0, 0, 0, 0]
    },
    "fehlercode_03": {
        "description": "LED 2 blinkt langsam, LED 4 und 5 an",
        "states": [0, 1, 0, 1, 1],
        "blink_ms": [0, 700, 0, 0, 0]
    },
    "fehlercode_04": {
        "description": "LED 3 blinkt schnell, LED 1 an",
        "states": [1, 0, 1, 0, 0],
        "blink_ms": [0, 0, 300, 0, 0]
    },
    "fehlercode_05": {
        "description": "LED 1, 2 und 3 blinken gemeinsam",
        "states": [1, 1, 1, 0, 0],
        "blink_ms": [500, 500, 500, 0, 0]
    }
}

ERROR_CODE_ORDER = [
    "fehlercode_01",
    "fehlercode_02",
    "fehlercode_03",
    "fehlercode_04",
    "fehlercode_05"
]


# ============================================================
# Globale Zustände
# ============================================================

leds = []
led_states = [0, 0, 0, 0, 0]

active_error_code = None
active_base_states = [0, 0, 0, 0, 0]
active_blink_ms = [0, 0, 0, 0, 0]
last_blink_toggle = [0, 0, 0, 0, 0]


# ============================================================
# LED-Steuerung
# ============================================================

def setup_leds():
    global leds

    leds = []

    for pin in LED_PINS:
        led = Pin(pin, Pin.OUT)
        led.off()
        leds.append(led)

    print("LEDs initialized")


def internal_set_led(index, state):
    if index < 0 or index >= len(leds):
        return False

    if state == 1:
        leds[index].on()
        led_states[index] = 1
    else:
        leds[index].off()
        led_states[index] = 0

    return True


def stop_error_code():
    global active_error_code
    global active_base_states
    global active_blink_ms

    active_error_code = None
    active_base_states = [0, 0, 0, 0, 0]
    active_blink_ms = [0, 0, 0, 0, 0]

    print("Error code stopped")


def set_led(index, state):
    stop_error_code()

    success = internal_set_led(index, state)

    if success:
        print("LED", index + 1, "set to", state)

    return success


def set_all_leds(state):
    stop_error_code()

    for i in range(len(leds)):
        internal_set_led(i, state)

    print("All LEDs set to", state)


def run_test_pattern():
    stop_error_code()

    print("Running test pattern")

    for i in range(len(leds)):
        internal_set_led(i, 1)
        sleep(0.2)
        internal_set_led(i, 0)

    sleep(0.3)

    for i in range(len(leds)):
        internal_set_led(i, 1)

    sleep(0.7)

    for i in range(len(leds)):
        internal_set_led(i, 0)


def play_error_code(code):
    global active_error_code
    global active_base_states
    global active_blink_ms
    global last_blink_toggle

    if code not in ERROR_CODES:
        return False

    definition = ERROR_CODES[code]

    active_error_code = code
    active_base_states = definition["states"][:]
    active_blink_ms = definition["blink_ms"][:]
    last_blink_toggle = [ticks_ms(), ticks_ms(), ticks_ms(), ticks_ms(), ticks_ms()]

    for i in range(len(leds)):
        internal_set_led(i, active_base_states[i])

    print("Playing error code:", code)

    return True


def update_blinking():
    if active_error_code is None:
        return

    now = ticks_ms()

    for i in range(len(leds)):
        interval = active_blink_ms[i]

        if interval > 0:
            if ticks_diff(now, last_blink_toggle[i]) >= interval:
                if led_states[i] == 1:
                    internal_set_led(i, 0)
                else:
                    internal_set_led(i, 1)

                last_blink_toggle[i] = now


# ============================================================
# WLAN / Update
# ============================================================

def get_ip_address():
    wlan = network.WLAN(network.STA_IF)

    if wlan.isconnected():
        return wlan.ifconfig()[0]

    return "not connected"


def check_update_safely():
    if updater is None:
        return

    try:
        print("Periodic/startup update check...")
        updater.check_for_update()
    except Exception as e:
        print("Update check failed:", e)


# ============================================================
# Hilfsfunktionen: URL, CSV, JSON
# ============================================================

def url_decode(value):
    if value is None:
        return ""

    value = value.replace("+", " ")

    result = ""
    i = 0

    while i < len(value):
        if value[i] == "%" and i + 2 < len(value):
            try:
                hex_value = value[i + 1:i + 3]
                result += chr(int(hex_value, 16))
                i += 3
            except Exception:
                result += value[i]
                i += 1
        else:
            result += value[i]
            i += 1

    return result


def csv_escape(value):
    if value is None:
        value = ""

    value = str(value)
    value = value.replace('"', '""')

    if "," in value or '"' in value or "\n" in value:
        return '"' + value + '"'

    return value


def file_exists(path):
    try:
        os.stat(path)
        return True
    except Exception:
        return False


def ensure_log_file():
    if not file_exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write(
                "created_ms,file_name,error_code,environment,"
                "roi_x,roi_y,roi_w,roi_h,"
                "lighting,camera_position,distance_cm,notes\n"
            )


def append_log_entry(data):
    ensure_log_file()

    row = [
        str(ticks_ms()),
        data.get("file", ""),
        data.get("code", ""),
        data.get("env", ""),
        data.get("roi_x", ""),
        data.get("roi_y", ""),
        data.get("roi_w", ""),
        data.get("roi_h", ""),
        data.get("lighting", ""),
        data.get("camera", ""),
        data.get("distance", ""),
        data.get("notes", "")
    ]

    line = ",".join([csv_escape(item) for item in row]) + "\n"

    with open(LOG_FILE, "a") as f:
        f.write(line)

    print("Log entry saved:", line)

    return True


def read_log_file():
    ensure_log_file()

    with open(LOG_FILE, "r") as f:
        return f.read()


def clear_log_file():
    if file_exists(LOG_FILE):
        os.remove(LOG_FILE)

    ensure_log_file()


def json_status():
    leds_json = ",".join([str(state) for state in led_states])

    if active_error_code is None:
        code_json = "null"
    else:
        code_json = '"' + active_error_code + '"'

    return (
        "{"
        '"leds":[' + leds_json + "],"
        '"active_error_code":' + code_json +
        "}"
    )


# ============================================================
# HTML
# ============================================================

def error_code_options_html():
    result = ""

    for code in ERROR_CODE_ORDER:
        definition = ERROR_CODES[code]
        label = code + " - " + definition["description"]
        result += '<option value="' + code + '">' + label + '</option>\n'

    return result


def html_page():
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ESP32 LED Evaluation Controller</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 24px;
            background: #f4f4f4;
        }

        .container {
            max-width: 1050px;
            margin: auto;
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.12);
        }

        h1 {
            margin-top: 0;
        }

        h2 {
            margin-top: 32px;
            border-top: 1px solid #ddd;
            padding-top: 20px;
        }

        .led-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px;
            margin-bottom: 10px;
            background: #f0f0f0;
            border-radius: 8px;
        }

        .status {
            font-weight: bold;
            min-width: 60px;
        }

        button {
            padding: 8px 14px;
            margin: 4px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            background: #222;
            color: white;
        }

        button.secondary {
            background: #666;
        }

        button.danger {
            background: #9b1c1c;
        }

        button:hover {
            opacity: 0.85;
        }

        input, select, textarea {
            width: 100%;
            box-sizing: border-box;
            padding: 8px;
            margin-top: 4px;
            margin-bottom: 12px;
            border: 1px solid #bbb;
            border-radius: 6px;
            font-size: 1rem;
        }

        textarea {
            min-height: 70px;
        }

        label {
            font-weight: bold;
        }

        .on {
            color: green;
        }

        .off {
            color: red;
        }

        .info {
            margin-top: 18px;
            font-size: 0.9rem;
            color: #555;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        @media (max-width: 800px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }

        .camera-box {
            position: relative;
            width: 100%;
            max-width: 900px;
            background: #111;
            border-radius: 10px;
            overflow: hidden;
        }

        #preview {
            width: 100%;
            display: block;
        }

        #overlay {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            cursor: crosshair;
        }

        .small {
            font-size: 0.9rem;
            color: #555;
        }

        .output {
            background: #f0f0f0;
            padding: 12px;
            border-radius: 8px;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 0.9rem;
        }

        .download-link {
            display: inline-block;
            margin-top: 8px;
            padding: 8px 14px;
            border-radius: 6px;
            background: #0b5;
            color: white;
            text-decoration: none;
        }
    </style>
</head>

<body>
<div class="container">
    <h1>ESP32 LED Evaluation Controller</h1>

    <p>
        Diese Oberfläche dient zur Datenerzeugung für die LED-Erkennung.
        Der ESP32 steuert die LEDs und speichert die Logdaten.
        Die Videoaufnahme erfolgt im Browser und wird lokal auf deinem Gerät gespeichert.
    </p>

    <h2>1. Fehlercode auswählen und abspielen</h2>

    <label for="errorCode">Fehlercode</label>
    <select id="errorCode">
""" + error_code_options_html() + """
    </select>

    <button onclick="playErrorCode()">Fehlercode abspielen</button>
    <button class="secondary" onclick="stopErrorCode()">Fehlercode stoppen</button>

    <p class="small">
        Aktiver Fehlercode: <span id="activeErrorCode">-</span>
    </p>

    <h2>2. Manuelle LED-Steuerung</h2>

    <div id="led-container"></div>

    <div>
        <button onclick="allOn()">Alle LEDs einschalten</button>
        <button onclick="allOff()">Alle LEDs ausschalten</button>
        <button onclick="runPattern()">Testmuster starten</button>
        <button onclick="refreshStatus()">Status aktualisieren</button>
    </div>

    <h2>3. Video aufnehmen und Router-Rechteck festlegen</h2>

    <p class="small">
        Starte die Kamera, zeichne mit der Maus oder dem Finger ein Rechteck um den Router
        und starte dann die Aufnahme. Das Video wird nach dem Stoppen als Datei zum Download angeboten.
    </p>

    <div class="camera-box">
        <video id="preview" autoplay muted playsinline></video>
        <canvas id="overlay"></canvas>
    </div>

    <div style="margin-top: 12px;">
        <button onclick="startCamera()">Kamera starten</button>
        <button onclick="startRecording()">Aufnahme starten</button>
        <button onclick="stopRecording()">Aufnahme stoppen</button>
        <button class="secondary" onclick="clearRoi()">Rechteck löschen</button>
    </div>

    <div id="downloadArea"></div>

    <p class="small">
        Rechteck relativ zum Videobild:
        <span id="roiText">kein Rechteck gesetzt</span>
    </p>

    <h2>4. Aufnahme dokumentieren</h2>

    <div class="grid">
        <div>
            <label for="fileName">Videodateiname</label>
            <input id="fileName" value="video_001.webm">

            <label for="environment">Umgebung</label>
            <select id="environment">
                <option value="labor">Labor</option>
                <option value="real">Reale Umgebung</option>
            </select>

            <label for="lighting">Lichtverhältnisse</label>
            <select id="lighting">
                <option value="">nicht angegeben</option>
                <option value="constant_light">konstantes Licht</option>
                <option value="daylight">Tageslicht</option>
                <option value="low_light">schwaches Licht</option>
                <option value="mixed_light">Mischlicht</option>
                <option value="reflections">Reflexionen sichtbar</option>
            </select>
        </div>

        <div>
            <label for="cameraPosition">Kameraposition</label>
            <select id="cameraPosition">
                <option value="">nicht angegeben</option>
                <option value="front">frontal</option>
                <option value="slightly_left">leicht links</option>
                <option value="slightly_right">leicht rechts</option>
                <option value="angled">schräg</option>
                <option value="handheld">aus der Hand gefilmt</option>
            </select>

            <label for="distance">Entfernung in cm</label>
            <input id="distance" type="number" placeholder="z. B. 80">

            <label for="notes">Notizen</label>
            <textarea id="notes" placeholder="z. B. Reflexionen, wackelige Kamera, dunkler Raum"></textarea>
        </div>
    </div>

    <button onclick="saveLogEntry()">Eintrag in ESP-Log speichern</button>
    <button onclick="loadLog()">Log anzeigen</button>
    <button class="danger" onclick="clearLog()">Log löschen</button>
    <a class="download-link" href="/api/logs" download="recordings.csv">CSV herunterladen</a>

    <h2>5. Aktuelle Logdatei</h2>
    <div id="logOutput" class="output">Noch nicht geladen.</div>

    <div class="info">
        <p>API-Endpunkte:</p>
        <p>/api/status</p>
        <p>/api/set?led=1&state=1</p>
        <p>/api/all?state=0</p>
        <p>/api/pattern</p>
        <p>/api/error?code=fehlercode_03</p>
        <p>/api/stop</p>
        <p>/api/log</p>
        <p>/api/logs</p>
    </div>
</div>

<script>
    let stream = null;
    let recorder = null;
    let recordedChunks = [];

    let roi = null;
    let drawing = false;
    let startX = 0;
    let startY = 0;

    const video = document.getElementById("preview");
    const canvas = document.getElementById("overlay");
    const ctx = canvas.getContext("2d");

    function resizeCanvasToVideo() {
        const rect = video.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = rect.height;
        drawRoi();
    }

    window.addEventListener("resize", resizeCanvasToVideo);

    video.addEventListener("loadedmetadata", () => {
        resizeCanvasToVideo();
    });

    function getPointerPosition(event) {
        const rect = canvas.getBoundingClientRect();

        let clientX;
        let clientY;

        if (event.touches && event.touches.length > 0) {
            clientX = event.touches[0].clientX;
            clientY = event.touches[0].clientY;
        } else {
            clientX = event.clientX;
            clientY = event.clientY;
        }

        return {
            x: clientX - rect.left,
            y: clientY - rect.top
        };
    }

    function startDraw(event) {
        event.preventDefault();

        const pos = getPointerPosition(event);

        drawing = true;
        startX = pos.x;
        startY = pos.y;

        roi = {
            x: startX,
            y: startY,
            w: 0,
            h: 0
        };

        drawRoi();
    }

    function moveDraw(event) {
        if (!drawing) {
            return;
        }

        event.preventDefault();

        const pos = getPointerPosition(event);

        roi = {
            x: Math.min(startX, pos.x),
            y: Math.min(startY, pos.y),
            w: Math.abs(pos.x - startX),
            h: Math.abs(pos.y - startY)
        };

        drawRoi();
    }

    function endDraw(event) {
        if (!drawing) {
            return;
        }

        event.preventDefault();

        drawing = false;
        updateRoiText();
    }

    canvas.addEventListener("mousedown", startDraw);
    canvas.addEventListener("mousemove", moveDraw);
    canvas.addEventListener("mouseup", endDraw);
    canvas.addEventListener("mouseleave", endDraw);

    canvas.addEventListener("touchstart", startDraw);
    canvas.addEventListener("touchmove", moveDraw);
    canvas.addEventListener("touchend", endDraw);

    function drawRoi() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (!roi) {
            return;
        }

        ctx.lineWidth = 3;
        ctx.strokeStyle = "red";
        ctx.strokeRect(roi.x, roi.y, roi.w, roi.h);

        ctx.fillStyle = "rgba(255, 0, 0, 0.15)";
        ctx.fillRect(roi.x, roi.y, roi.w, roi.h);
    }

    function clearRoi() {
        roi = null;
        drawRoi();
        updateRoiText();
    }

    function getNormalizedRoi() {
        if (!roi || canvas.width === 0 || canvas.height === 0) {
            return {
                x: "",
                y: "",
                w: "",
                h: ""
            };
        }

        return {
            x: (roi.x / canvas.width).toFixed(4),
            y: (roi.y / canvas.height).toFixed(4),
            w: (roi.w / canvas.width).toFixed(4),
            h: (roi.h / canvas.height).toFixed(4)
        };
    }

    function updateRoiText() {
        const r = getNormalizedRoi();

        if (r.x === "") {
            document.getElementById("roiText").innerText = "kein Rechteck gesetzt";
            return;
        }

        document.getElementById("roiText").innerText =
            "x=" + r.x + ", y=" + r.y + ", w=" + r.w + ", h=" + r.h;
    }

    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: "environment"
                },
                audio: false
            });

            video.srcObject = stream;

            setTimeout(resizeCanvasToVideo, 500);
        } catch (error) {
            alert("Kamera konnte nicht gestartet werden: " + error);
        }
    }

    async function startRecording() {
        if (!stream) {
            await startCamera();
        }

        recordedChunks = [];

        try {
            if (MediaRecorder.isTypeSupported("video/webm;codecs=vp9")) {
                recorder = new MediaRecorder(stream, {
                    mimeType: "video/webm;codecs=vp9"
                });
            } else if (MediaRecorder.isTypeSupported("video/webm")) {
                recorder = new MediaRecorder(stream, {
                    mimeType: "video/webm"
                });
            } else {
                recorder = new MediaRecorder(stream);
            }

            recorder.ondataavailable = function(event) {
                if (event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };

            recorder.onstop = function() {
                const blob = new Blob(recordedChunks, {
                    type: "video/webm"
                });

                const url = URL.createObjectURL(blob);
                const fileName = document.getElementById("fileName").value || "video.webm";

                const downloadArea = document.getElementById("downloadArea");
                downloadArea.innerHTML = "";

                const link = document.createElement("a");
                link.href = url;
                link.download = fileName;
                link.innerText = "Video herunterladen: " + fileName;
                link.className = "download-link";

                downloadArea.appendChild(link);
            };

            recorder.start();

            alert("Aufnahme gestartet.");
        } catch (error) {
            alert("Aufnahme konnte nicht gestartet werden: " + error);
        }
    }

    function stopRecording() {
        if (recorder && recorder.state !== "inactive") {
            recorder.stop();
            alert("Aufnahme gestoppt. Das Video kann jetzt heruntergeladen werden.");
        }
    }

    async function refreshStatus() {
        const response = await fetch("/api/status");
        const data = await response.json();

        const container = document.getElementById("led-container");
        container.innerHTML = "";

        if (data.active_error_code === null) {
            document.getElementById("activeErrorCode").innerText = "-";
        } else {
            document.getElementById("activeErrorCode").innerText = data.active_error_code;
        }

        data.leds.forEach((state, index) => {
            const row = document.createElement("div");
            row.className = "led-row";

            const label = document.createElement("div");
            label.innerText = "LED " + (index + 1);

            const status = document.createElement("div");
            status.className = "status " + (state === 1 ? "on" : "off");
            status.innerText = state === 1 ? "AN" : "AUS";

            const buttons = document.createElement("div");

            const onButton = document.createElement("button");
            onButton.innerText = "An";
            onButton.onclick = () => setLed(index + 1, 1);

            const offButton = document.createElement("button");
            offButton.innerText = "Aus";
            offButton.onclick = () => setLed(index + 1, 0);

            buttons.appendChild(onButton);
            buttons.appendChild(offButton);

            row.appendChild(label);
            row.appendChild(status);
            row.appendChild(buttons);

            container.appendChild(row);
        });
    }

    async function setLed(led, state) {
        await fetch("/api/set?led=" + led + "&state=" + state);
        await refreshStatus();
    }

    async function allOn() {
        await fetch("/api/all?state=1");
        await refreshStatus();
    }

    async function allOff() {
        await fetch("/api/all?state=0");
        await refreshStatus();
    }

    async function runPattern() {
        await fetch("/api/pattern");
        await refreshStatus();
    }

    async function playErrorCode() {
        const code = document.getElementById("errorCode").value;
        await fetch("/api/error?code=" + encodeURIComponent(code));
        await refreshStatus();
    }

    async function stopErrorCode() {
        await fetch("/api/stop");
        await refreshStatus();
    }

    async function saveLogEntry() {
        const r = getNormalizedRoi();

        const params = new URLSearchParams();

        params.append("file", document.getElementById("fileName").value);
        params.append("code", document.getElementById("errorCode").value);
        params.append("env", document.getElementById("environment").value);
        params.append("roi_x", r.x);
        params.append("roi_y", r.y);
        params.append("roi_w", r.w);
        params.append("roi_h", r.h);
        params.append("lighting", document.getElementById("lighting").value);
        params.append("camera", document.getElementById("cameraPosition").value);
        params.append("distance", document.getElementById("distance").value);
        params.append("notes", document.getElementById("notes").value);

        const response = await fetch("/api/log?" + params.toString());
        const data = await response.json();

        if (data.ok) {
            alert("Logeintrag gespeichert.");
            await loadLog();
        } else {
            alert("Fehler beim Speichern des Logeintrags.");
        }
    }

    async function loadLog() {
        const response = await fetch("/api/logs");
        const text = await response.text();

        document.getElementById("logOutput").innerText = text;
    }

    async function clearLog() {
        const confirmed = confirm("Logdatei wirklich löschen?");

        if (!confirmed) {
            return;
        }

        await fetch("/api/clear-log");
        await loadLog();
    }

    refreshStatus();
    loadLog();
</script>
</body>
</html>
"""


# ============================================================
# HTTP Request Parsing
# ============================================================

def parse_request_path(request):
    try:
        first_line = request.split("\r\n")[0]
        parts = first_line.split(" ")

        if len(parts) >= 2:
            return parts[1]

    except Exception as e:
        print("Request parse error:", e)

    return "/"


def parse_query(path):
    result = {}

    if "?" not in path:
        return result

    query_string = path.split("?", 1)[1]
    pairs = query_string.split("&")

    for pair in pairs:
        if "=" in pair:
            key, value = pair.split("=", 1)
            result[key] = url_decode(value)
        else:
            result[pair] = ""

    return result


def send_all(client, data):
    chunk_size = 512

    for i in range(0, len(data), chunk_size):
        client.send(data[i:i + chunk_size])


def send_response(client, body, content_type="text/html", status="200 OK"):
    if isinstance(body, str):
        body_bytes = body.encode("utf-8")
    else:
        body_bytes = body

    header = (
        "HTTP/1.1 " + status + "\r\n"
        "Content-Type: " + content_type + "\r\n"
        "Content-Length: " + str(len(body_bytes)) + "\r\n"
        "Connection: close\r\n"
        "\r\n"
    )

    send_all(client, header.encode("utf-8"))
    send_all(client, body_bytes)


# ============================================================
# Routing
# ============================================================

def handle_request(path):
    print("Request:", path)

    if path == "/" or path.startswith("/?"):
        return html_page(), "text/html", "200 OK"

    if path.startswith("/api/status"):
        return json_status(), "application/json", "200 OK"

    if path.startswith("/api/set"):
        query = parse_query(path)

        try:
            led_number = int(query.get("led", "0"))
            state = int(query.get("state", "0"))

            led_index = led_number - 1

            success = set_led(led_index, state)

            if success:
                return json_status(), "application/json", "200 OK"

            return '{"error":"invalid led index"}', "application/json", "400 Bad Request"

        except Exception as e:
            print("Set LED error:", e)
            return '{"error":"invalid request"}', "application/json", "400 Bad Request"

    if path.startswith("/api/all"):
        query = parse_query(path)

        try:
            state = int(query.get("state", "0"))
            set_all_leds(state)
            return json_status(), "application/json", "200 OK"

        except Exception as e:
            print("Set all LEDs error:", e)
            return '{"error":"invalid request"}', "application/json", "400 Bad Request"

    if path.startswith("/api/pattern"):
        run_test_pattern()
        return json_status(), "application/json", "200 OK"

    if path.startswith("/api/error"):
        query = parse_query(path)
        code = query.get("code", "")

        success = play_error_code(code)

        if success:
            return json_status(), "application/json", "200 OK"

        return '{"error":"unknown error code"}', "application/json", "400 Bad Request"

    if path.startswith("/api/stop"):
        stop_error_code()

        for i in range(len(leds)):
            internal_set_led(i, 0)

        return json_status(), "application/json", "200 OK"

    if path.startswith("/api/log?"):
        query = parse_query(path)

        try:
            append_log_entry(query)
            return '{"ok":true}', "application/json", "200 OK"

        except Exception as e:
            print("Log save error:", e)
            return '{"ok":false}', "application/json", "500 Internal Server Error"

    if path.startswith("/api/logs"):
        try:
            return read_log_file(), "text/csv", "200 OK"

        except Exception as e:
            print("Log read error:", e)
            return "error", "text/plain", "500 Internal Server Error"

    if path.startswith("/api/clear-log"):
        try:
            clear_log_file()
            return '{"ok":true}', "application/json", "200 OK"

        except Exception as e:
            print("Log clear error:", e)
            return '{"ok":false}', "application/json", "500 Internal Server Error"

    return "Not found", "text/plain", "404 Not Found"


# ============================================================
# Webserver
# ============================================================

def start_server():
    ip = get_ip_address()

    print("ESP32 IP address:", ip)
    print("Open in browser: http://" + ip)

    address = socket.getaddrinfo("0.0.0.0", 80)[0][-1]

    server_socket = socket.socket()

    try:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception:
        pass

    server_socket.bind(address)
    server_socket.listen(3)

    server_socket.settimeout(1)

    print("Webserver started on port 80")

    return server_socket


# ============================================================
# Main Loop
# ============================================================

def main():
    setup_leds()
    ensure_log_file()

    print("LED evaluation controller started")

    check_update_safely()

    server_socket = start_server()

    last_update_check = ticks_ms()

    while True:
        update_blinking()

        try:
            client, client_address = server_socket.accept()

            try:
                request = client.recv(4096).decode("utf-8")
                path = parse_request_path(request)

                body, content_type, status = handle_request(path)
                send_response(client, body, content_type, status)

            except Exception as e:
                print("Client handling error:", e)

            finally:
                client.close()

        except OSError:
            pass

        except Exception as e:
            print("Server error:", e)
            sleep(1)

        now = ticks_ms()

        if ticks_diff(now, last_update_check) >= UPDATE_INTERVAL_MS:
            check_update_safely()
            last_update_check = now


main()