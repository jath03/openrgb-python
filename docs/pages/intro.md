# Introduction

OpenRGB-Python is a client for the [OpenRGB SDK](https://gitlab.com/CalcProgrammer1/OpenRGB#openrgb-sdk),
a manufacturer-independent, cross-platform way to control your RGB devices.
OpenRGB-Python can be used to interface with other programs, create custom
effects, or anything else you can think of!

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

## Installation

requires python >= 3.7

Use this method for the newest, but possibly buggy, package:

`pip3 install git+https://github.com/jath03/openrgb-python#egg=openrgb-python`

Arch Linux:
`yay -S python-openrgb-git`

For a more stable package:

`pip3 install openrgb-python`

Arch Linux:
`yay -S python-openrgb`

Thanks to [@GabMus](https://github.com/GabMus) for the AUR packages
