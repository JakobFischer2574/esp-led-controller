import machine
import os

try:
    import urequests as requests
except ImportError:
    import requests

import version


def _parse_version(value):
    parts = value.split(".")
    return tuple(int(p) for p in parts)


def _is_remote_newer(local, remote):
    try:
        return _parse_version(remote) > _parse_version(local)
    except Exception:
        # Fallback: Bei ungueltigem Format nur auf Ungleichheit pruefen
        return remote != local


def _download_text(url):
    response = requests.get(url)
    try:
        if response.status_code != 200:
            raise Exception("HTTP {} fuer {}".format(response.status_code, url))
        return response.text
    finally:
        response.close()


def _write_file_atomic(target_path, content):
    tmp_path = target_path + ".tmp"

    with open(tmp_path, "w") as tmp_file:
        tmp_file.write(content)

    try:
        os.remove(target_path)
    except OSError:
        pass

    os.rename(tmp_path, target_path)


def _update_version_file(new_version):
    content = 'VERSION = "{}"\n'.format(new_version)
    _write_file_atomic("version.py", content)


def check_for_update():
    try:
        import config
    except ImportError:
        print("Keine config.py gefunden. Update wird uebersprungen.")
        return

    try:
        manifest_text = _download_text(config.MANIFEST_URL)

        try:
            import ujson as json
        except ImportError:
            import json

        manifest = json.loads(manifest_text)
        remote_version = manifest.get("version")
        files = manifest.get("files", [])

        if not remote_version:
            print("Manifest ohne Version. Update wird uebersprungen.")
            return

        if not _is_remote_newer(version.VERSION, remote_version):
            print("Keine neue Version. Lokal:", version.VERSION)
            return

        print("Neue Version gefunden:", remote_version)

        for file_name in files:
            file_url = "{}/{}".format(config.UPDATE_BASE_URL.rstrip("/"), file_name)
            print("Lade", file_url)
            content = _download_text(file_url)
            _write_file_atomic(file_name, content)

        _update_version_file(remote_version)
        print("Update abgeschlossen. Neustart...")
        machine.reset()

    except Exception as exc:
        print("Update fehlgeschlagen:", exc)
        print("System laeuft mit bestehender Version weiter.")
