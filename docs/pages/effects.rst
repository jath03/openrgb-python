Writing Custom Effects
======================
This method of setting colors was made to be similar (on the front end) to other
LED control libraries like FastLED or adafruit's Neopixel library.  It was also
optimized better for speed, making it more suitable to creating custom effects
that require a fast refresh rate.

Basics
------
OpenRGB devices with a "direct" mode are the best to use with effects, because
in that mode they don't save colors to flash storage or have any flickering
problems at higher refresh rates.  You can control only these devices by using
the :any:`OpenRGBClient.ee_devices` property instead of the
:any:`OpenRGBClient.devices` list.

.. code-block:: python

    from openrgb import OpenRGBClient

    cli = OpenRGBClient()

    print(cli.devices)
    print(cli.ee_devices)

FastLED-like Control Flow
-------------------------
This control method follows a pattern of setting color values, and then calling
a function to apply the changed values to the physical LEDs. Here is an example
for setting a device to a rainbow color.

.. code-block:: python

    from openrgb import OpenRGBClient
    from openrgb.utils import RGBColor

    cli = OpenRGBClient()

    # dividing the color spectrum by number of LEDs
    step = int(len(cli.ee_devices[0].colors)/360)
    for i, hue in enumerate(range(0, 360, step)):
        cli.ee_devices[0].colors[i] = RGBColor.fromHSV(hue, 100, 100)
    cli.ee_devices[0].show()
