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

3. ### Force screen resolution
Edit `/boot/firmware/cmdline.txt`, adding the explicit video mode which also enables screen hotplug
e.g. video=HDMI-A-1:1280x720M@60D
Mode specification is defined at: https://github.com/raspberrypi/linux/blob/rpi-6.1.y/Documentation/fb/modedb.rst

4. ### Reboot

5. ### Rotate display and force resolution (not needed on pikiosk-east)
    1. Create `/etc/xdg/autostart/xrandr.desktop`
    2. Fill it with:
    ```
    [Desktop Entry]
    Type=Application
    Name=Display rotation
    Exec=xrandr --output HDMI-1 --rotate left --mode 1280x720
    ```

Use `Exec=xrandr --output HDMI-1 --rotate left --mode 1280x720` for rotate.

6. ### Disable splash screen
    1. Rgb -> add disable_splash=1 to `/boot/firmware/config.json`
    2. Disable PI splash -> Remove `splash` from `/boot/firmware/cmdline.txt` 
    3. Disable boot logs -> Add `quiet loglevel=0 consoleblank=1` to `/boot/firmware/cmdline.txt`

7. ### Hide cursor after timeout 
    1. sudo apt update
    2. sudo apt install unclutter
    3. Create `/etc/xdg/autostart/unclutter.desktop`
    ```
    [Desktop Entry]
    Type=Application
    Name=Hide cursor
    Exec=unclutter -idle 10 -root
    ```

8. ### Prevent display from falling asleep
    1. Turn off display blanking in raspi-config
    2. Create `/etc/xdg/autostart/nosleep.desktop`
    ```
    [Desktop Entry]
    Type=Application
    Name=No sleep
    Exec=sh -c "xset s off -dpms s noblank"
    ```

9. ### Install piosk
    1. `curl -sSL https://raw.githubusercontent.com/debloper/piosk/v4.0.0/scripts/setup.sh | sudo bash -`
    2. Edit `/opt/piosk/scripts/runner.sh` 
        1. Edit chromium-browser to just chromium

10. ### Sudo reboot 

11. ### Disable usb (udev)
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

12. ### Disable config website
    1. Run `sudo systemctl disable piosk-dashboard.service`
    2. The config can be edited manually by editing `/opt/piosk/config.json`
    3. The webpage itself is in `~/Documents/`

13. ### Schedule period webpage update from git
    Use crontab -e (here for the East Wing):
    ```
    0 23 * * * wget -O /home/pikiosk/Documents/webpage/index.html https://raw.githubusercontent.com/philharrisathome/TCCKiosk/refs/heads/main/TCCEastWingEvents.html
    ```

13. ### Turn screen off outside hours
    Use crontab -e:
    ```
    0 23 * * * export DISPLAY=:0 && /usr/bin/xset dpms force off
    0 6 * * * export DISPLAY=:0 && /usr/bin/xset dpms force on && /usr/bin/xset s off && /usr/bin/xset s noblank
    ```

# Notes
If chromium won't start due to locked profile: https://github.com/puppeteer/puppeteer/issues/4860
Show current mode: kmsprint
Show available modes: kmsprint -m

# JVC screen modes (West Wing)
`1366x768@61.72` does not work - horizontal tearing
`1280x720@60` works ok.

pikiosk@pikiosk-west:~ $ kmsprint -m
Connector 0 (33) HDMI-A-1 (connected)
   0 1366x768@61.72    85.500 1366/110/40/220/+  768/5/5/20/+       62 (61.72) P|D
   1 1920x1080@60.00  148.500 1920/88/44/148/+   1080/4/5/36/+      60 (60.00) D     16:9
   2 1920x1080@59.94  148.352 1920/88/44/148/+   1080/4/5/36/+      60 (59.94) D     16:9
   3 1920x1080i@60.00  74.250 1920/88/44/148/+   1080/4/10/31/+     60 (60.00) D     16:9
   4 1920x1080i@59.94  74.176 1920/88/44/148/+   1080/4/10/31/+     60 (59.94) D     16:9
   5 1920x1080@50.00  148.500 1920/528/44/148/+  1080/4/5/36/+      50 (50.00) D     16:9
   6 1920x1080i@50.00  74.250 1920/528/44/148/+  1080/4/10/31/+     50 (50.00) D
   7 1920x1080i@50.00  74.250 1920/528/44/148/+  1080/4/10/31/+     50 (50.00) D     16:9
   8 1920x1080@30.00   74.250 1920/88/44/148/+   1080/4/5/36/+      30 (30.00) D     16:9
   9 1920x1080@29.97   74.176 1920/88/44/148/+   1080/4/5/36/+      30 (29.97) D     16:9
  10 1920x1080@25.00   74.250 1920/528/44/148/+  1080/4/5/36/+      25 (25.00) D     16:9
  11 1920x1080@24.00   74.250 1920/638/44/148/+  1080/4/5/36/+      24 (24.00) D     16:9
  12 1920x1080@23.98   74.176 1920/638/44/148/+  1080/4/5/36/+      24 (23.98) D     16:9
  13 1280x720i@128.29  74.250 1280/88/44/148/+   720/2/5/15/+       128 (128.29) D
  14 1280x720@60.00    74.250 1280/110/40/220/+  720/5/5/20/+       60 (60.00) U|D   16:9
  15 1280x720@59.94    74.176 1280/110/40/220/+  720/5/5/20/+       60 (59.94) D     16:9
  16 1280x720@50.00    74.250 1280/440/40/220/+  720/5/5/20/+       50 (50.00) D
  17 1280x720@50.00    74.250 1280/440/40/220/+  720/5/5/20/+       50 (50.00) D     16:9
  18 1024x768@60.00    65.000 1024/24/136/160/-  768/3/6/29/-       60 (60.00) D
  19 800x600@60.32     40.000 800/40/128/88/+    600/1/4/23/+       60 (60.32) D
  20 720x576@50.00     27.000 720/12/64/68/-     576/5/5/39/-       50 (50.00) D
  21 720x576@50.00     27.000 720/12/64/68/-     576/5/5/39/-       50 (50.00) D     16:9
  22 720x576i@50.00    13.500 720/12/63/69/-     576/4/6/39/-       50 (50.00) D     2x|16:9
  23 720x480@60.00     27.027 720/16/62/60/-     480/9/6/30/-       60 (60.00) D     4:3
  24 720x480@60.00     27.027 720/16/62/60/-     480/9/6/30/-       60 (60.00) D     16:9
  25 720x480@59.94     27.000 720/16/62/60/-     480/9/6/30/-       60 (59.94) D
  26 720x480@59.94     27.000 720/16/62/60/-     480/9/6/30/-       60 (59.94) D     16:9
  27 720x480i@60.00    13.514 720/19/62/57/-     480/8/6/31/-       60 (60.00) D     2x|16:9
  28 720x480i@59.94    13.500 720/19/62/57/-     480/8/6/31/-       60 (59.94) D     2x|16:9
