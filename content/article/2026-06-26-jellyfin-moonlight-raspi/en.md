---
title: Streaming games and Jellyfin on a Raspberry Pi 4
description: Building a low-power Raspberry Pi 4 kiosk that streams games from a workstation and video from Jellyfin
tags: [raspberry-pi, debian, moonlight, jellyfin, wayland, cage]
---


# The goal

I wanted a small, low-power box that does exactly two things:

- Stream games from my main workstation, controller in hand, no keyboard required.
- Play video from my Jellyfin server.

No login screen, no desktop to navigate, nothing. For video, there's nothing to launch by hand either. I just open a Jellyfin client (the [mobile app](https://jellyfin.org/docs/general/clients/) or the [web player](https://jellyfin.org/docs/general/clients/)) on my phone or a another machine, hit **Cast to Device**, and pick the Pi from the list. [jellyfin-mpv-shim](https://github.com/jellyfin/jellyfin-mpv-shim) registers itself on the network as exactly that kind of castable target, so it shows up next to any Chromecasts or other Jellyfin clients already on the LAN.


# The stack

- **Debian trixie**: what I run everywhere by default.
- **Raspberry Pi 4**: already had one lying around.
- **[moonlight-qt](https://github.com/moonlight-stream/moonlight-qt)** for game streaming. It's the open-source client for NVIDIA's GameStream protocol (and, here, for [Sunshine](https://github.com/LizardByte/Sunshine), which plays the role of the streaming host on the workstation side).
- **[jellyfin-mpv-shim](https://github.com/jellyfin/jellyfin-mpv-shim)** for video. It's a lightweight Jellyfin client that uses [mpv](https://mpv.io/) as its playback backend and gets remote-controlled by other Jellyfin apps on the network, similar in spirit to a Chromecast.
- **[Cage](https://github.com/cage-kiosk/cage)**, a Wayland compositor built specifically for kiosk setups. A "kiosk" is just a machine locked into running a single full-screen application, with no window manager chrome, no taskbar, and no easy way out to a desktop.

## Why bother with a compositor at all?

Both moonlight-qt and mpv can [run directly against the kernel's DRI/DRM layer](https://linuxvox.com/blog/linux-dri/), without Xorg or Wayland in the picture. But when they do, each one grabs exclusive ownership of the GPU, fine if only one of them ever runs, useless the moment you want both moonlight and video playback available on the same machine.

Cage solves that by sitting in between and brokering GPU access. I picked it because it does one thing: run an application full-screen, and get out of the way. The setup here always keeps moonlight-qt running and visible, except when jellyfin-mpv-shim starts a video, at which point mpv takes over the screen until playback stops.

## A word on audio

No PulseAudio, no PipeWire: just [ALSA](https://www.alsa-project.org/). Nothing here ever needs to mix two audio streams at once, so there's no reason to drag in a sound server. I'll try this for few weeks and see if a sound server is actually required in the long run.

I'm also using the Pi's analog audio jack instead of HDMI audio:

- It's the default output, so zero extra configuration.
- No audio/video sync issues so far, a known risk when audio and video don't travel over the same HDMI link.
- On a previous setup, I got odd audio artifacts through the projector's HDMI input: something like a noise gate that was way too slow to open. I'm not sure if the projector or the (very cheap) speakers were at fault, but routing audio straight out of the Pi's jack sidesteps the question entirely.

# Sunshine on the workstation

Sunshine acts as the streaming host: the thing moonlight-qt on the Pi connects to. There's no Debian repo for it yet, so we grab the `.deb` straight from GitHub releases.

```sh
wget https://github.com/LizardByte/Sunshine/releases/download/v2026.516.143833/sunshine-debian-trixie-amd64.deb
sudo apt install ./sunsine-debian-trixie-amd64.deb

# Allow Sunshine to access the KMS/DRM graphics subsystem for low-latency capture
sudo setcap cap_sys_admin+p $(readlink -f $(which sunshine))

# Grant gamepad and mouse input access to your user
# Check first with the `groups` command if it's not already there
# If not, a reboot or at least a log out / log in is required
# after adding a new group to an user
sudo usermod -aG input $USER
```

Once it's back up, enable the user service so Sunshine starts automatically:

```sh
systemctl --user enable --now app-dev.lizardbyte.app.Sunshine.service
```

That unit name looks like a Flatpak app ID because it is one: the `.deb` is really just a Flatpak bundle with a thin wrapper around it, not a native package. It still installs and runs through `apt` like you'd expect, but under the hood it's `flatpak` doing the work, which is why the systemd unit follows Flatpak's reverse-DNS naming instead of a plain `sunshine.service`.

It sits idle at essentially zero CPU/memory when nothing is streaming, so there's no harm in leaving it always on.

The systemd unit shipped with the Debian package doesn't inherit your shell's `PATH`. That means any command Sunshine runs needs to be given as a full path: `steam` alone won't resolve.

- Open the [Sunshine configuration panel](https://localhost:47990).
- Go to **Applications → Steam Big Picture → Edit**.
- In both the **Detached commands** and **Undo command** fields, change `setsid steam` to `setsid /usr/games/steam`.
- Save.

![Set the full path to steam in the Sunshine configuration](sunshine.png)

# Raspberry Pi preparation

I flashed [Raspberry Pi OS Lite](https://www.raspberrypi.com/software/operating-systems/) to start from a minimal base. Only what is needed is going to be installed, minimizing maintenance problems are speeding up the install.

Flashing itself was slightly fiddly: I run [sway](https://swaywm.org/) as my desktop, and [rpi-imager](https://github.com/raspberrypi/rpi-imager) needs to run as root, which on Wayland means going through XWayland in a [somewhat unusual way](https://charlesfleche.net/rpi-imager-on-wayland/).

Once booted, the [moonlight documentation](https://github.com/moonlight-stream/moonlight-docs/wiki/Fixing-Hardware-Decoding-Problems#raspberry-pi) recommends bumping the memory reserved for the GPU:

```sh
echo "gpu_mem=128" | sudo tee -a /boot/config.txt
sudo reboot
```

# Installing Moonlight

Nothing fancy here: the [official install script](https://github.com/moonlight-stream/moonlight-docs/wiki/Installing-Moonlight-Qt-on-Raspberry-Pi-4) handles adding the repository:

```sh
curl -1sLf \
  'https://dl.cloudsmith.io/public/moonlight-game-streaming/moonlight-qt/setup.deb.sh' \
  | distro=raspbian codename=$(lsb_release -cs) sudo -E bash
sudo apt install moonlight-qt
```

# jellyfin-mpv-shim

## Installing it

`mpv`, the video player itself, comes straight from the Debian repos. `jellyfin-mpv-shim` doesn't have a Debian package, so it's installed from the [Python Package Index](https://pypi.org/project/jellyfin-mpv-shim/). And [pipx](https://pipx.pypa.io/) handles fetching it into its own isolated environment and dropping the executable on your `PATH`.

```sh
sudo apt install pipx mpv
pipx install jellyfin-mpv-shim
pipx inject jellyfin-mpv-shim pillow  # silences a warning in the logs
pipx ensurepath
jellyfin-mpv-shim  # run once to generate the initial configuration
```

## Tuning mpv

The Pi 4's CPU is too slow to decode video smoothly on its own. We need to force mpv to use the GPU. The two settings that matter most are `profile=fast` and `vo=gpu-next` (so `hwdec=v4l2m2m-copy` is available). Everything else in the config below is fine-tuning on top of that.

`jellyfin-mpv-shim` keeps its own `mpv.conf`, separate from mpv's own default one. That split confused me more than once while benchmarking mpv standalone, so I just symlink the two together:

```sh
mkdir -p ~/.config/mpv
ln -s ~/.config/jellyfin-mpv-shim/mpv.conf ~/.config/mpv/mpv.conf
```

`~/.config/jellyfin-mpv-shim/mpv.conf`:

```ini
# --- Hardware decoding ---
hwdec=v4l2m2m-copy
vd-lavc-dr=no

# --- Video output ---
vo=gpu-next
gpu-api=opengl

# --- Fast decoding profile ---
profile=fast

# --- Scaling (cheap, since the Pi 4 GPU is weak) ---
scale=bilinear
dscale=bilinear
cscale=bilinear
dither=no
correct-downscaling=no
linear-downscaling=no
sigmoid-upscaling=no

# --- Reduce OSD/OSC overhead ---
osc=no
osd-level=1

# --- Avoid unnecessary color/HDR processing ---
hdr-compute-peak=no
target-colorspace-hint=no

# --- Audio ---
audio-channels=stereo
# Pre-listing pipewire and pulse just in case I need them one day,
# instead of spending an hour wondering why audio is stuck on alsa
ao=pipewire,pulse,alsa

# --- Cache / smoother seeking on network shares (e.g. Jellyfin) ---
cache=yes
demuxer-max-bytes=64MiB
demuxer-readahead-secs=10

# --- Framedrop on overload rather than desync ---
framedrop=vo

# --- Avoid heavy subtitle rendering ---
sub-font-size=32
```

## Cage

Three things left: install Cage, write a small script that launches both apps and set up autologin so the Pi boots straight into them.

The launch script. Note the full paths to the binaries (important once this runs under systemd, where `PATH` can't be trusted) and the explicit `QT_QPA_PLATFORM=wayland`, to make sure moonlight-qt talks to Cage directly instead of accidentally falling back to XWayland.

`/home/charles/startup-apps.sh`:

```sh
!/usr/bin/env bash
export QT_QPA_PLATFORM=wayland
/usr/bin/moonlight-qt &
exec /home/charles/.local/bin/jellyfin-mpv-shim
```

Both processes need to stay alive together, so only the last one in the script gets `exec`'d (replacing the shell), the first one is backgrounded with `&`.

Don't forget to make it executable:

```sh
chmod +x /home/charles/startup-apps.sh
```

Next, the systemd unit that autologs the `charles` user straight into Cage on boot, saved as `/etc/systemd/system/display-manager.service`. This is a trimmed-down version of the unit suggested in [Cage's own documentation](https://github.com/cage-kiosk/cage/wiki/Starting-Cage-on-boot-with-systemd/d1f06017c22413058524f616004f03ab1af0328a).

```ini
# This is a system unit for launching Cage with auto-login as the
# user configured here. For this to work, wlroots must be built
# with systemd-logind support.

[Unit]
Description=Cage Wayland compositor
# Make sure we are started after logins are permitted. If Plymouth is
# used, we want to start when it is on its way out.
After=systemd-user-sessions.service plymouth-quit-wait.service
# Since we are part of the graphical session, make sure we are started
# before it is complete.
Before=graphical.target
# On systems without virtual consoles, do not start.
ConditionPathExists=/dev/tty0
# D-Bus is necessary for contacting logind, which is required.
Wants=dbus.socket systemd-logind.service
After=dbus.socket systemd-logind.service
# Replace any (a)getty that may have spawned, since we log in
# automatically.
Conflicts=getty@tty1.service
After=getty@tty1.service

[Service]
Type=simple
ExecStart=/usr/bin/cage -sd -- /home/charles/startup-apps.sh
Restart=always
User=charles
# Log this user with utmp, letting it show up with commands 'w' and
# 'who'. This is needed since we replace (a)getty.
UtmpIdentifier=tty1
UtmpMode=user
# A virtual terminal is needed.
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
TTYVTDisallocate=yes
# Fail to start if not controlling the virtual terminal.
StandardInput=tty-fail

# Set up a full (custom) user session for the user, required by Cage.
PAMName=cage

[Install]
WantedBy=graphical.target
```

Finally, install Cage, disable whatever could fight it for the same TTY, and tell systemd to boot graphically:

```sh
# Install cage
sudo apt install cage

# Stop the standard console login from blocking that same TTY
sudo systemctl disable getty@tty1.service

# Default to the graphical target instead of a plain console
sudo systemctl set-default graphical.target

# Enable our autologin unit
sudo systemctl enable display-manager.service
```

# Ready to stream

And that's it. After a reboot, the Pi boots straight into moonlight-qt and sits there, waiting. Hit "stream" from the workstation and you're playing Steam Big Picture games on the TV. Open Jellyfin from your phone or any web browser on the LAN and hit "cast": mpv pops up full-screen, plays the video, and hands control back to moonlight the moment it's done.

