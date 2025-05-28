Title: SIM management with mmcli
Description: Unlock a SIM on Linux with mmcli

Broken phone, broken screen and a broken digitizer. It kept on registering random touches on the SIM PIN screen, unfortunately blocking it. My backup phone does not offer to enter the [PUK PIN](https://en.wikipedia.org/wiki/Personal_unblocking_key), so I had to find another way to unlock the SIM. Thankfully I have a [Mobian](https://mobian-project.org/) compatible [Pinephone](https://pine64.org/devices/pinephone/). A quick `apt install modemmanager` later, `sudo mmcli -i 0 --pin=<pin_number> --puk=<puk_number>` eventually unlocked the SIM.

Tips courtesy of [https://discourse.ubuntu.com/t/entering-sim-passwords/19909](https://discourse.ubuntu.com/t/entering-sim-passwords/19909).
