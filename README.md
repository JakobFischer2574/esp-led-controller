# esp-led-controller

Ein einfaches MicroPython-Projekt fuer einen ESP32 mit 5 LEDs und einem robusten Pull-Update-Mechanismus ueber GitHub Raw.

## Zweck

- `main.py` fuehrt dauerhaft ein LED-Testmuster aus.
- Beim Start prueft `main.py` einmal, ob im Repository eine neuere Version verfuegbar ist.
- Der ESP32 zieht Updates selbststaendig (Pull-Prinzip), ohne dass GitHub direkt auf den ESP pusht.

## Struktur

```text
esp-led-controller/
├── esp/
│   ├── boot.py
│   ├── main.py
│   ├── updater.py
│   ├── version.py
│   └── config.example.py
├── manifest.json
├── tools/
│   └── deploy_initial.ps1
├── .gitignore
└── README.md
```

## config.py erstellen

1. `esp/config.example.py` nach `esp/config.py` kopieren.
2. Werte setzen:
   - `WIFI_SSID`
   - `WIFI_PASSWORD`
   - `UPDATE_BASE_URL` (Raw-URL zum Ordner `esp`)
   - `MANIFEST_URL` (Raw-URL zur `manifest.json`)

Beispiel:

```powershell
copy esp\config.example.py esp\config.py
```

> `esp/config.py` ist in `.gitignore` eingetragen und darf nicht committet werden.

## Initiales Deployment (Windows + mpremote)

Voraussetzung: `mpremote` ist installiert und der ESP ist per USB verbunden.

1. In `tools/deploy_initial.ps1` den COM-Port anpassen (`$PORT`, z. B. `COM3`).
2. Script ausfuehren:

```powershell
.\tools\deploy_initial.ps1
```

Das Script kopiert `boot.py`, `main.py`, `updater.py`, `version.py` und `config.py` auf den ESP und fuehrt danach einen Reset aus.

## Update-Ablauf

Beim Start:

1. `boot.py` versucht WLAN aufzubauen (bei Fehlern laeuft das System weiter).
2. `main.py` ruft `updater.check_for_update()` einmal auf.
3. `updater.py` laedt `manifest.json` von `MANIFEST_URL`.
4. Versionsvergleich mit lokaler `version.py`.
5. Wenn remote neuer ist:
   - alle Dateien aus `manifest.json` von `UPDATE_BASE_URL` laden,
   - erst als `.tmp` speichern,
   - dann atomar ersetzen,
   - `version.py` auf neue Version setzen,
   - `machine.reset()` ausfuehren.

Wenn WLAN/HTTP/Manifest fehlschlaegt, bleibt die vorhandene Firmware aktiv und das LED-Testprogramm laeuft weiter.

## Wichtiger Hinweis fuer neue Releases

Damit der ESP ein Update laedt, muss die Version in `manifest.json` erhoeht werden (z. B. von `0.0.1` auf `0.0.2`).
Wenn die Version gleich bleibt, wird kein Update eingespielt.

## Sicherheit

- WLAN-Zugangsdaten niemals committen.
- `esp/config.py` lokal halten.
