# Credentials
| Hostname       | MAC                 | Username  | Password     |
| -------------- | ------------------- | --------- | ------------ |
| `pikiosk-east` | `dc:a6:32:65:5f:6c` | `pikiosk` | `T0Display3` | 
| `pikiosk-west` | `88:a2:9e:6e:ef:43` | `pikiosk` | `T0Display3` | 

# SD Card
Create partitions as below:

```
Disk /dev/sda: 29.54 GiB, 31719424000 bytes, 61952000 sectors
Disk model: SD/MMC          
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
Disklabel type: dos
Disk identifier: 0x42bfd89c

Device     Boot   Start      End  Sectors  Size Id Type
/dev/sda1         16384  1064959  1048576  512M  c W95 FAT32 (LBA)
/dev/sda2       1064960 61951966 60887007   29G 83 Linux
```

Copy `pikiosk_1.img` to partition 1. Copy `pikiosk_2.img` to partition 2.

# Setup
1. ### Sudo raspi-config
    1. Set boot to desktop
    2. Display -> Overscan compensation -> yes
    2. Interface -> ssh
    3. Advanced -> expand filesystem
    4. Advanced -> wayland to x11 (for mouse dissapear)
2. ### sudo apt update + upgrade + install chromium
3. ### Reboot
4. ### Rotate display and change resolution 
    1. Create `/etc/xdg/autostart/xrandr.desktop`
    2. Fill it with:
    ```
    [Desktop Entry]
    Type=Application
    Name=Display rotation
    Exec=xrandr --output HDMI-1 --rotate left --mode 1280x720
    ```

5. ### Disable splash screen
    1. Rgb -> add disable_splash=1 to `/boot/firmware/config.json`
    2. Disable PI splash -> Remove `splash` from `/boot/firmware/cmdline.txt` 
    3. Disable boot logs -> Add `quiet loglevel=0 consoleblank=1` to `/boot/firmware/cmdline.txt`
6. ### Hide cursor after timeout 
    1. sudo apt update
    2. sudo apt install unclutter
    3. Create `/etc/xdg/autostart/unclutter.desktop`
    ```
    [Desktop Entry]
    Type=Application
    Name=Hide cursor
    Exec=unclutter -idle 10 -root
    ```

7. ### Install piosk
    1. `curl -sSL https://raw.githubusercontent.com/debloper/piosk/v4.0.0/scripts/setup.sh | sudo bash -`
    2. Edit `/opt/piosk/scripts/runner.sh` 
        1. Edit chromium-browser to just chromium
8. ### Sudo reboot 
9. ### Disable usb (udev)
    1. Create script at `/usr/local/bin/disable-usb.sh`
    ```
    #!/bin/bash
    # Safely unbind all USB devices except the Pi4 USB hub (Ethernet included)

    for dev in /sys/bus/usb/devices/*; do
        # Skip root hubs
        [[ -f "$dev/idVendor" ]] && vendor=$(cat "$dev/idVendor") || continue
        [[ "$vendor" == "2109" ]] && continue  # Pi4 USB hub
        [[ ! -f "$dev/driver/unbind" ]] && continue  # Skip if no driver

        # Unbind the device
        echo "${dev##*/}" | sudo tee "$dev/driver/unbind"
    done
    ```
    2. `sudo chmod +x /usr/local/bin/disable-usb.sh`
    3. Create `/etc/systemd/system/disable-usb.service` with:
    ```
    [Unit]
    Description=Disable all USB devices except Ethernet
    After=network.target

    [Service]
    Type=oneshot
    ExecStart=/usr/local/bin/disable-usb.sh
    RemainAfterExit=yes

    [Install]
    WantedBy=multi-user.target
    ```
    5. `sudo systemctl enable disable-usb.service`
    6. `sudo systemctl start disable-usb.service`

10. ### Disable config website
    1. Run `sudo systemctl disable piosk-dashboard.service`
    2. The config can be edited manually by editing `/opt/piosk/config.json`
    3. The webpage itself is in `~/Documents/`

11. ### Prevent display from falling asleep
    1. Turn off display blanking in raspi-config
    2. Create `/etc/xdg/autostart/nosleep.desktop`
    ```
    [Desktop Entry]
    Type=Application
    Name=No sleep
    Exec=sh -c "xset s off -dpms s noblank"
    ```

12. ### Turn screen off outside hours
    Use crontab -e:
    ```
    0 23 * * * export DISPLAY=:0 && /usr/bin/xset dpms force off
    0 6 * * * export DISPLAY=:0 && /usr/bin/xset dpms force on && /usr/bin/xset s off && /usr/bin/xset s noblank
    ```

# Notes
Show current mode: kmsprint
Show available modes: kmsprint -m
Set modes: sudo nano /boot/firmware/cmdline.txt
e.g. video=HDMI-A-1:720x400M@70D
