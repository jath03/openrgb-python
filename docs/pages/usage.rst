Basic Usage
===========

Initialization
--------------
Initializing an :any:`OpenRGBClient` is pretty simple.

.. code-block:: python

    from openrgb import OpenRGBClient
    cli = OpenRGBClient()

That's it as long as you are controlling a local OpenRGB SDK, using the default
port, and don't want to change the name.  If this is not the case, there are a
few more options.

.. code-block:: python

    cli = OpenRGBClient('192.168.1.111', 8000, 'My client!')

This will connect to an OpenRGB SDK server at :code:`192.168.1.111:8000` with
the name :code:`My client!`.

Selecting Devices
-----------------
On initialization, the :any:`OpenRGBClient` will create :any:`Device` objects
for all of your OpenRGB Devices.  You can list these out by :code:`print`-ing
:code:`cli.devices`.  Devices can be accessed through their index in this list,
but this is not ideal, especially for programs that will be used over a longer
period of time.  This is because the device's index could change if a new device
is added, or the order of OpenRGB's detectors is changed.  Another, more
consistent way to get a specific device is through its device type.

.. code-block:: python

    from openrgb.utils import DeviceType

    mobo = cli.get_devices_by_type(DeviceType.MOTHERBOARD)[0]

If you have more than one device of a specific type, then you can try filtering
by the devices' metadata, name, or any other property.

Setting colors
--------------
Colors are handled by the :any:`RGBColor` object.  It can be initialized from
RGB, HSV, or even HEX color values.

.. code-block:: python

    from openrgb.utils import RGBColor
    red = RGBColor(255, 0, 0)
    blue = RGBColor.fromHSV(240, 100, 100)
    green = RGBColor.fromHEX('#00ff00') # The '#' symbol isn't necessary, it's just commonly attached to HEX colors

.. note::

    Already familiar with other LED control libraries like fastLED or adafruit's
    neopixel library?  The :doc:`effects control flow</pages/effects>`
    was made to be used in a similar way.  Try it out and see which one you like
    better!

Any :any:`RGBObject` object can be set to an :any:`RGBColor` using a few
methods. :any:`RGBObject` is the parent class of basically everything.

To set an :any:`RGBObject` to a solid color, use the
:any:`set_color<RGBObject.set_color>` function.

.. code-block:: python

    mobo.set_color(RGBColor(0, 255, 0))
    cli.devices[0].set_color(red)
    cli.devices[1].zones[0].set_color(blue)

.. warning::

	Setting the color for the same device more than once without some kind of delay in between can cause undefined behavior.


If you want to set an :any:`RGBContainer` to more than one color, use the
:any:`set_colors<Device.set_colors>` function.  This example assumes that the
motherboard has 8 LEDs, and sets them in a red, blue, red, blue... pattern.

.. code-block:: python

    mobo.set_colors([red, blue]*4)

.. note::

    While these methods can be used for things like custom effects, it requires
    a little more effort to make it work quickly enough (see
    :doc:`optimizing for speed</pages/advanced>`). The
    :doc:`effects control flow</pages/effects>` was made to be easier
    to use for effects that require fast changes.


Both of these methods can be used to only set part of an object.  For example,
for a motherboard with 8 LEDs, this would set the middle 4 to red.

.. code-block:: python

    mobo.set_color(red, 2, 6)

Changing Modes
--------------
A device's modes can be found under :code:`Device.modes`, in the form of
:any:`ModeData` objects.  Modes can be set for a device through the
:any:`Device.set_mode` function.  The mode can be passed in via index, name, or
you can pass in the actual mode object.

.. code-block:: python

    mobo.set_mode(3)
    mobo.set_mode('direct')
    mobo.set_mode(mobo.modes[2])

Resizing Zones
--------------
If you have a device with a 35 LED ARGB zone, then you will probably need to
resize it at some point.

.. code-block:: python

    mobo.zones[0].resize(35)

Using Profiles
--------------
Once you have set your RGB exactly how you like it, you probably want to save
the state into a profile.  This function will save the current state of you
lights to a profile.

.. code-block:: python

    cli.save_profile('perfection')

This will save a profile called perfection.orp in OpenRGB's config directory by
default, so you can load the profile directly from OpenRGB's profile list.

Loading profiles in OpenRGB-Python is equally as simple as saving them.  This
function will set your lights to the same as they were when they were saved.
It can load profiles saved from OpenRGB itself, or OpenRGB-Python.

.. code-block:: python

    cli.load_profile('perfection')

.. warning::

    I only know where OpenRGB's config directory is on linux and I haven't
    tested saving profiles on windows.  The default directory that
    OpenRGB-Python saves profiles is :code:`~/.config/OpenRGB`. If you know
    where OpenRGB's config directory is on windows and how to reliably find it
    from python, please submit a pr or come talk to me on OpenRGB's discord
    server.  In the mean time, you will probably have to manually specify the
    directory where you want to save or load a profile from using the
    :code:`directory` argument.
