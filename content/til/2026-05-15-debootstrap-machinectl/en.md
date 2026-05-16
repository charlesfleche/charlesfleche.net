Title: A minimal debian for machinectl
Description: Preparing a minimal machine for machinectl

I sometime need a quick, minimal debian server to test a package without compromising my main workstation. This machine has an uncommon networking setup, so I need [`systemd-resolved`](https://www.freedesktop.org/software/systemd/man/latest/systemd-resolved.service.html) installed on the guest early.

```
# /etc/systemd/nspawn/my-container.nspawn
#
# This strip down sample shows the container network configuration.
# It needs to be named as the container. Here: my-container.nspawn

[Network]
VirtualEthernet=yes

[Exec]
ResolvConf=bind-uplink
```

```sh
# First, we create the minimal base system

sudo debootstrap --variant=minbase --include=dbus,systemd-container stable /var/lib/machines/my-container https://deb.debian.org/debian/


# Then, we start the container and open a sheel

sudo machinectl start my-container
sudo machinectl shell my-container

# Lastly, we make sure the the networkd service is enabled and running

systemctl enable --now systemd-networkd

networkctl
IDX LINK  TYPE     OPERATIONAL SETUP     
  1 lo    loopback carrier     unmanaged
  2 host0 ether    routable    configured

2 links listed.
```

