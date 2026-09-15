Title: Root encrypted mobian on pinephone
Description:
Tags:

./build.sh -t sunxi -e plasma-mobile -c -R some_luks_password -u charles -p user_password
sudo bmaptool copy mobian-sunxi-plasma-mobile-20260823.img /dev/sdi

TowBoot

1. Expand the Partition Table

Use parted to push partition 2 (the encrypted root) to 100% of the 32GB eMMC disk capacity:  
Bash

sudo parted /dev/sdi resizepart 2 100%

2. Expand the LUKS Container

Open the encrypted volume and instruct cryptsetup to expand the underlying device boundaries:  
Bash

# Open the LUKS volume
sudo cryptsetup luksOpen /dev/sdi2 mobian_crypt

# Resize the decrypted container to fill the block device
sudo cryptsetup resize mobian_crypt

3. Expand the Filesystem


lsblk -f /dev/mapper/mobian_crypt


Depending on the filesystem you chose when building your custom Mobian image:  

    For ext4:  
    Bash

    sudo e2fsck -f /dev/mapper/mobian_crypt
    sudo resize2fs /dev/mapper/mobian_crypt

    For f2fs (Mobian default):  
    Bash

    sudo resize.f2fs /dev/mapper/mobian_crypt

Step 3: Clean Up

Close the decrypted container, safely unmount, and reboot:  
Bash

sudo cryptsetup luksClose mobian_crypt

