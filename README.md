---
BlueProximity
---
>This software helps you add a little more security to your
desktop. It does so by detecting one of your bluetooth devices,
most likely your mobile phone, and keeping track of its distance.

[![Python Version][python-image]][python-url]

>## Note from the maintainer of this fork ##
>Version **2.0** is a Qt6 / KDE rewrite (PySide6). GTK3, Glade and
Ayatana AppIndicator have been removed. Existing configs in
`~/.blueproximity/` remain compatible.
> - Marco Faenzi

## Description from the original author
>If you move away from your computer and the distance is above
a certain level for a given time, it automatically locks your desktop
(or starts any other shell command you want).

>Once away your computer awaits its master back - if you are
nearer than a given level for a set time your computer unlocks
magically without any interaction
(or starts any other shell command you want).

## Installation

### Ubuntu 26.04 LTS (Plasma 6 / Wayland) — Qt6 edition

Build and install the Debian package from source:

```sh
sudo apt install debhelper python3-pyside6.qtwidgets python3-configobj
cd blueproximity
# or use the manual packaging script / prebuilt .deb
sudo apt install ../blueproximity_2.0.0-1_all.deb
```

Runtime dependencies (installed automatically with the package):

```sh
sudo apt install python3-pyside6.qtcore python3-pyside6.qtgui \
  python3-pyside6.qtwidgets python3-configobj python3-bluez \
  python3-dbus bluez qdbus-qt6
```

Run from a source checkout:

```sh
cd blueproximity
PYTHONPATH=. python3 -m blueproximity
```

On Plasma 6 the default lock/unlock commands use `loginctl` and the
freedesktop ScreenSaver D-Bus interface via `qdbus6`. Pair your phone
via Bluetooth and configure its MAC address in Preferences.

### Development setup

```sh
cd blueproximity
pip3 install -r requirements.txt   # configobj / pybluez as needed
# system packages: python3-pyside6.qtwidgets python3-bluez python3-dbus
PYTHONPATH=. python3 -m blueproximity
```

## Configuration

Settings live in `~/.blueproximity/*.conf` (ConfigObj). No path editing
is required; resource paths are auto-detected from the install location.

## Release History

* 2.0.0 Qt6 / KDE rewrite (PySide6), system tray StatusNotifierItem
* 1.4.x Plasma 6 / Wayland GTK fixes, Debian packaging
* 1.3.3 Bug fixes
* 1.3.0 Updated application so it now runs in Python 3 and GTK+ 3

## License
Distributed under the GPL v.2 license. See ``COPYING`` for more information.

[python-image]: https://img.shields.io/badge/python-3.8+-blue
[python-url]: https://www.python.org/downloads/release/python-370/
