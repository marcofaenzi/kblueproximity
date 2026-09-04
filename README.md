---
KBlueProximity
---
>This software helps you add a little more security to your
desktop. It does so by detecting one of your bluetooth devices,
most likely your mobile phone, and keeping track of its distance.

[![Python Version][python-image]][python-url]

>## Note ##
>**KBlueProximity** is the Qt6 / KDE fork of BlueProximity (PySide6).
GTK3, Glade and Ayatana AppIndicator have been removed. Existing configs
from `~/.blueproximity/` are copied to `~/.kblueproximity/` on first run.

## Description from the original author
>If you move away from your computer and the distance is above
a certain level for a given time, it automatically locks your desktop
(or starts any other shell command you want).

>Once away your computer awaits its master back - if you are
nearer than a given level for a set time your computer unlocks
magically without any interaction
(or starts any other shell command you want).

## Installation

### Ubuntu 26.04 LTS (Plasma 6 / Wayland)

```sh
sudo apt install ../kblueproximity_2.2.0-1_all.deb
```

Runtime dependencies (installed automatically with the package):

```sh
sudo apt install python3-pyside6.qtcore python3-pyside6.qtgui \
  python3-pyside6.qtwidgets python3-configobj python3-bluez \
  python3-dbus bluez qdbus-qt6
```

Run from a source checkout:

```sh
PYTHONPATH=. python3 -m kblueproximity
```

On Plasma 6 the default lock/unlock commands use `loginctl` and the
freedesktop ScreenSaver D-Bus interface via `qdbus6`. Pair your phone
via Bluetooth and configure its MAC address in Preferences.

## Configuration

Settings live in `~/.kblueproximity/*.conf` (ConfigObj).

## Release History

* 2.2.0 Renamed application to KBlueProximity (Qt6 / KDE fork)
* 2.1.x Thresholds / Environment UI, scan period, tray UX
* 2.0.0 Qt6 / KDE rewrite (PySide6)
* 1.4.x Plasma 6 / Wayland GTK fixes
* 1.3.0 Python 3 and GTK+ 3

## License
Distributed under the GPL v.2 license. See ``COPYING`` for more information.

[python-image]: https://img.shields.io/badge/python-3.8+-blue
[python-url]: https://www.python.org/downloads/release/python-370/
