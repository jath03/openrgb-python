Frequently Asked Questions
==========================

Why is my code giving weird errors and/or crashing OpenRGB?
-----------------------------------------------------------
The most common error I've seen is trying to interact with a device too quickly.
Whenever you do something to one device, make sure to have some kind of delay
before doing something else with the same device.  This applies to changing
modes, colors, or even resizing a zone.

What does the :code:`fast` parameter do?
----------------------------------------
Many functions that involve setting colors have a :code:`fast` parameter.  When
set to :code:`False` (the default), the function will update the status of the
device you are controlling each time you call a function.  This is done so that
the :any:`OpenRGBClient` always has the correct information about what mode your
device is in, what colors are currently set...  Setting the parameter to
:code:`True`, skips this step, which is faster.

.. note::

	You should only need to use this parameter if you want an effect or something to run quickly, and you are willing the accuracy of the internal state.

        Before using the :code:`fast` parameter, look to see if your use case might be better suited to the :doc:`effects control flow</pages/effects>`.

Why does my program only work when <device> isn't connected?
---------------------------------------------------------------
Most device-specific issues are problems with OpenRGB itself.  Look for issues
regarding your device on `OpenRGB's gitlab <https://gitlab.com/CalcProgrammer1/OpenRGB/-/issues/>`_.


My RGB device(s) isn't doing what I want!
-----------------------------------------
One easy way to figure out whether the problem is with OpenRGB or openrgb-python
is to look at the device view in OpenRGB.  If the colors there look like they're
supposed to, then openrgb-python and your code are correct, and OpenRGB is
setting your device incorrectly.  If the colors in the device view don't look
correct, you probably messed up your program.  If not, open an issue on this
`library's github page <https://github.com/jath03/openrgb-python/>`_.

What is "Direct" mode?
----------------------
`<https://gitlab.com/CalcProgrammer1/OpenRGB/-/wikis/Common-Modes/>`_




Also see `OpenRGB's FAQ page <https://gitlab.com/CalcProgrammer1/OpenRGB/-/wikis/Frequently-Asked-Questions/>`_.
