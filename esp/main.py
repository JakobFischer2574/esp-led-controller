from machine import Pin
from time import sleep

import updater


LED_PINS = [14, 27, 25, 32, 33]


def setup_leds():
    leds = []
    for pin in LED_PINS:
        leds.append(Pin(pin, Pin.OUT))
    return leds


def all_leds_off(leds):
    for led in leds:
        led.off()


def run_test_pattern(leds):
    # LEDs nacheinander einschalten
    for led in leds:
        led.on()
        sleep(0.3)
        led.off()

    sleep(0.5)

    # Alle LEDs gleichzeitig einschalten
    for led in leds:
        led.on()
        sleep(1)
        led.off()
        sleep(1)
        led.on()

    sleep(1)

    # Alle LEDs ausschalten
    all_leds_off(leds)
    sleep(1)


def main():
    leds = setup_leds()

    try:
        updater.check_for_update()
    except Exception as exc:
        print("Update-Check fehlgeschlagen:", exc)

    while True:
        run_test_pattern(leds)


main()
