import network
import time

try:
    import config
except Exception as e:
    print("config.py konnte nicht geladen werden:", e)
    config = None


def explain_status(status):
    if status == network.STAT_IDLE:
        return "idle"
    if status == network.STAT_CONNECTING:
        return "connecting"
    if status == network.STAT_WRONG_PASSWORD:
        return "wrong password"
    if status == network.STAT_NO_AP_FOUND:
        return "access point not found"
    if status == network.STAT_CONNECT_FAIL:
        return "connection failed"
    if status == network.STAT_GOT_IP:
        return "got ip"
    return "unknown status: {}".format(status)


def connect_wifi():
    if config is None:
        print("Kein WLAN möglich, weil config.py fehlt oder fehlerhaft ist.")
        return False

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("Bereits verbunden:", wlan.ifconfig())
        return True

    print("Verbinde mit WLAN:", config.WIFI_SSID)

    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

    timeout_seconds = 30
    start = time.time()

    while not wlan.isconnected():
        status = wlan.status()
        print("WLAN status:", status, explain_status(status))

        if time.time() - start > timeout_seconds:
            print("WLAN-Verbindung fehlgeschlagen. Starte normal weiter.")
            return False

        time.sleep(2)

    print("WLAN verbunden:", wlan.ifconfig())
    return True


connect_wifi()