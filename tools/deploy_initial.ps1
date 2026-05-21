$PORT = "COM16"

py -3.13 -m mpremote connect $PORT fs cp esp/boot.py :boot.py
py -3.13 -m mpremote connect $PORT fs cp esp/main.py :main.py
py -3.13 -m mpremote connect $PORT fs cp esp/updater.py :updater.py
py -3.13 -m mpremote connect $PORT fs cp esp/version.py :version.py
py -3.13 -m mpremote connect $PORT fs cp esp/config.py :config.py

py -3.13 -m mpremote connect $PORT reset