$PORT = "COM3"

mpremote connect $PORT fs cp esp/boot.py :boot.py
mpremote connect $PORT fs cp esp/main.py :main.py
mpremote connect $PORT fs cp esp/updater.py :updater.py
mpremote connect $PORT fs cp esp/version.py :version.py
mpremote connect $PORT fs cp esp/config.py :config.py

mpremote connect $PORT reset
