Title: Running rpi-imager as a normal user on debian / wayland
Description: Working around policykit and X11
Tags:

My debian workstation runs sway on wayland, but the latest [rpi-imager](https://downloads.raspberrypi.org/imager/imager_latest_amd64.deb) is actually a X11 only AppImage that needs to run as root. To run it, I hence need to:

- wrap it under policy kit authentication as no agent is running in the background
- allow X11
- pass some environment variables.

So:

```bash
xhost +SI:localuser:root
pkexec \
  env \
  DISPLAY=$DISPLAY \
  XAUTHORITY=$XAUTHORITY \
  QT_QPA_PLATFORM=xcb \
  rpi-imager
```

