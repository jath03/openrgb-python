Alternative Usage
=================
This method of setting colors was made to be similar (on the front end) to other
LED control libraries like FastLED or adafruit's Neopixel library.  It was also
optimized better for speed, making it more suitable to creating custom effects
that require a fast refresh rate.

Basics
------
This control method follows a pattern of setting color values, and then calling
a function to apply the changed values to the physical LEDs. Here is an example
for setting a device to a rainbow color.

.. code-block:: python

    from openrgb import OpenRGBClient
    from openrgb.utils import RGBColor

    cli = OpenRGBClient()

    # dividing the color spectrum by number of LEDs
    step = int(len(cli.devices[0].colors)/360)
    for i, hue in enumerate(range(0, 360, step)):
        cli.devices[0].colors[i] = RGBColor.fromHSV(hue, 100, 100)
    cli.devices[0].show()
