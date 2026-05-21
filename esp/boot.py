import network
from time import sleep


def connect_wifi():
    try:
        import config
    except ImportError:
        print("Keine config.py gefunden. WLAN wird uebersprungen.")
        return False

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("WLAN bereits verbunden:", wlan.ifconfig())
        return True

    print("Verbinde mit WLAN...")
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

    for _ in range(20):
        if wlan.isconnected():
            print("WLAN verbunden:", wlan.ifconfig())
            return True
        sleep(0.5)

    print("WLAN-Verbindung fehlgeschlagen. Starte normal weiter.")
    return False


try:
    connect_wifi()
except Exception as exc:
    print("WLAN-Fehler:", exc)
    print("Starte ohne WLAN weiter.")
