from machine import Pin
from time import sleep, ticks_ms, ticks_diff
import network
import socket

try:
    import updater
except Exception as e:
    updater = None
    print("Updater not available:", e)


# LED-Pins
LED_PINS = [14, 27, 25, 32, 33]

# Update-Check alle 60 Sekunden
UPDATE_INTERVAL_MS = 60_000

leds = []
led_states = [0, 0, 0, 0, 0]


def setup_leds():
    global leds

    leds = []

    for pin in LED_PINS:
        led = Pin(pin, Pin.OUT)
        led.off()
        leds.append(led)

    print("LEDs initialized")


def set_led(index, state):
    if index < 0 or index >= len(leds):
        return False

    if state == 1:
        leds[index].on()
        led_states[index] = 1
    else:
        leds[index].off()
        led_states[index] = 0

    print("LED", index + 1, "set to", state)
    return True


def set_all_leds(state):
    for i in range(len(leds)):
        set_led(i, state)


def run_test_pattern():
    print("Running test pattern")

    for i in range(len(leds)):
        set_led(i, 1)
        sleep(0.2)
        set_led(i, 0)

    sleep(0.3)

    set_all_leds(1)
    sleep(0.7)

    set_all_leds(0)


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


def html_page():
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ESP32-LED-Controller (ELC)</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 24px;
            background: #f4f4f4;
        }

        .container {
            max-width: 700px;
            margin: auto;
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.12);
        }

        h1 {
            margin-top: 0;
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
            margin-left: 6px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            background: #222;
            color: white;
        }

        button:hover {
            opacity: 0.85;
        }

        .actions {
            margin-top: 24px;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>ESP32-LED-Controller (ELC)</h1>

        <div id="led-container"></div>

        <div class="actions">
            <button onclick="allOn()">Alle LEDs einschalten</button>
            <button onclick="allOff()">Alle LEDs ausschalten</button>
            <button onclick="runPattern()">Testmuster starten</button>
            <button onclick="refreshStatus()">Status aktualisieren</button>
        </div>

        <div class="info">
            <p>API:</p>
            <p>/api/status</p>
            <p>/api/set?led=1&state=1</p>
            <p>/api/all?state=0</p>
            <p>/api/pattern</p>
        </div>
    </div>

    <script>
        async function refreshStatus() {
            const response = await fetch("/api/status");
            const data = await response.json();

            const container = document.getElementById("led-container");
            container.innerHTML = "";

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

        refreshStatus();
    </script>
</body>
</html>
"""


def json_status():
    return '{"leds":[' + ",".join([str(state) for state in led_states]) + "]}"


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
            result[key] = value

    return result


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

    client.send(header.encode("utf-8"))
    client.send(body_bytes)


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

            # Weboberfläche nutzt LED 1 bis LED 5.
            # Intern nutzen wir Index 0 bis 4.
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

    return "Not found", "text/plain", "404 Not Found"


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

    # Wichtig, damit der Update-Check im Loop weiterlaufen kann.
    server_socket.settimeout(1)

    print("Webserver started on port 80")

    return server_socket


def main():
    setup_leds()

    print("LED web controller started")

    # Einmal beim Start auf Updates prüfen.
    check_update_safely()

    server_socket = start_server()

    last_update_check = ticks_ms()

    while True:
        try:
            client, client_address = server_socket.accept()

            try:
                request = client.recv(1024).decode("utf-8")
                path = parse_request_path(request)

                body, content_type, status = handle_request(path)
                send_response(client, body, content_type, status)

            except Exception as e:
                print("Client handling error:", e)

            finally:
                client.close()

        except OSError:
            # Timeout vom server_socket.accept().
            # Das ist normal und erlaubt uns, regelmäßig Updates zu prüfen.
            pass

        except Exception as e:
            print("Server error:", e)
            sleep(1)

        now = ticks_ms()

        if ticks_diff(now, last_update_check) >= UPDATE_INTERVAL_MS:
            check_update_safely()
            last_update_check = now


main()