# openrgb-python


[![Documentation Status](https://readthedocs.org/projects/openrgb-python/badge/?version=latest)](https://openrgb-python.readthedocs.io/en/latest/?badge=latest)

A python client for the [OpenRGB SDK](https://gitlab.com/CalcProgrammer1/OpenRGB)

I started this project because I wanted to be able to control the color of my lights based on temps. I tried to implement the features in the best (easiest to use) way possible.  

SDK Feature Support:
  - [x] Setting client name
  - [x] Getting device info
  - [x] Setting color by device
  - [x] Setting color by zone
  - [x] Setting color by led
  - [x] Setting mode
  - [x] Setting custom mode
  - [x] Resizing zones

Additional Features (Not part of the OpenRGB SDK):
  - [x] Loading profiles
  - [x] Saving profiles

# Installation

requires python >= 3.7

Use this method for the newest, but possibly buggy, package:

`pip3 install git+https://github.com/jath03/openrgb-python#egg=openrgb-python`

Arch Linux:
`yay -S python-openrgb-git`

For a more stable package:

`pip3 install openrgb-python`

Arch Linux:
`yay -S python-openrgb`

Thanks to @GabMus for the AUR packages

# Usage

```python
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType

client = OpenRGBClient()

client.clear() # Turns everything off

motherboard = client.get_devices_by_type(DeviceType.MOTHERBOARD)[0]

motherboard.set_color(RGBColor(0, 255, 0))
motherboard.zones[0].set_color(RGBColor(255, 0, 0))
motherboard.zones[1].leds[0].set_color(RGBColor.fromHSV(0, 100, 100))
motherboard.set_mode("breathing")
client.save_profile("profile1")
```

# API Documentation

https://openrgb-python.readthedocs.io/en/latest/


For an alternative python implementation, check out [B Horn](https://github.com/bahorn)'s [OpenRGB-PyClient](https://github.com/bahorn/OpenRGB-PyClient)
