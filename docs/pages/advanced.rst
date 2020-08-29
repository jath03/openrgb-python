Advanced Usage
==============

Modifying Modes
---------------
If you want to change things like a mode's speed, you will need to edit the mode.
Before you do this, make sure that the property you want to edit is allowed in
that mode.  There are few ways to test this.

*  You can look in the OpenRGB GUI, select the mode you want to edit, and
   check if the option to edit the property is changeable or grayed out.
* You can check if the property you want to change is :code:`None`

.. code-block:: python

    if mode.speed is None:
        print("Speed not supported")
    if mode.direction is None:
        print("Direction not supported")
    ...

* You can check the mode's :any:`ModeFlags`

.. code-block:: python

    if ModeFlags.HAS_SPEED in mode.flags:
        print("Speed supported")
    if ModeFlags.HAS_MODE_SPECIFIC_COLOR in mode.flags:
        print("Mode specific color supported")

After you verify that the property that you want to change is supported by the
mode, you can edit it.  This can be done by directly editing a mode's properties

.. code-block:: python

    rainbow = cli.devices[0].modes[3]
    rainbow.speed = 0
    cli.devices[0].set_mode(rainbow)

.. warning::

	Most properties have a min and a max.  For speed, make sure to set the :code:`mode.speed` value to something between :code:`mode.speed_min` and :code:`mode.speed_max`.

Or more compactly:

.. code-block:: python

    cli.devices[0].modes[2].colors = [RGBColor(255, 0, 0), RGBColor(0, 0, 255)]
    cli.devices[0].set_mode(2)


Optimizing for Speed
--------------------
For creating custom effects, you often want to have your lights refreshing
quickly.  Optimizing openrgb-python for speed isn't very hard if you know what
you are doing.  The best way to maximize speed is to minimize OpenRGB SDK calls.
The most user-friendly way to do this is to use the
:doc:`alternative control</pages/alternate>` method, but it is possible to do
accomplish the same things with the other functions.  One common argument that
will help is the :code:`fast` argument.  In any of the color-changing functions
(:code:`set_color`, :code:`set_colors`, :code:`show`), if you pass in
:code:`True` to the :code:`fast` argument it will sacrifice internal state
management for speed.  The way it does this is by skipping the
:any:`RGBObject.update` call.  This is fine to use as long as you know what it
does, or rather doesn't do.

Minimizing SDK calls means converting code like this...

.. code-block:: python

    cli.devices[0].set_color(RGBColor(255, 0, 0))
    cli.devices[0].set_color(RGBColor(0, 255, 0), 4, 8)
    cli.devices[0].zones[0].set_color(RGBColor(0, 0, 255))

... into code like this (assuming the first zone is 3 LEDs long)

.. code-block:: python

    cli.devices[0].set_colors(
        [RGBColor(0, 0, 255)]*3 \
        + [RGBColor(255, 0, 0)] \
        + [RGBColor(0, 255, 0)]*4
    )

Which is pretty ugly, but only uses one SDK call, which makes it faster.  The
alternative control method is basically a better looking way of writing the
above code.

.. code-block:: python

    cli.devices[0].colors = [RGBColor(255, 0, 0)]*8
    cli.devices[0].colors[:3] = [RGBColor(0, 0, 255)]*3
    cli.devices[0].colors[4:8] = [RGBColor(0, 255, 0)]*4
    cli.devices[0].show()

Controlling the SDK Connection
------------------------------
For background programs, or programs that deal with an OpenRGB SDK server that
is not always on, you might want to start and stop the connection to the SDK
sometimes.

.. code-block:: python

    cli.disconnect()
    time.sleep(5)
    cli.connect()

When dealing with an unreliable SDK server (you don't know when it is on), you
will probably want some error handling.  If there is no SDK server running and
you try to call :any:`OpenRGBClient.connect()` or try to initialize an
:any:`OpenRGBClient`, then a :code:`ConnectionRefusedError` will be raised.  If
the client loses connection to the SDK server after the initial connection, then
trying to interact with the SDK server will cause an :any:`OpenRGBDisconnected`
error.
