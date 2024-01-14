# Raspberry Pi Audio Client Installation notes

Installing on a Raspberry Pi OS Lite 64-bit (Released 2023-05-03)

First find desired audio output: `cat /proc/asound/card*/id`

Set default audio output to the desired one (#TODO: test command): `sudo sed -i 's/card 0/card E30/g' ~/.asoundrc` - file needs to be created first, e. g. by setting the sound output with `sudo raspi-config`, maybe better to set name of soundcard instead of number, document how to find this

Link sound configuration to default/root configuration: `sudo ln -s ~/.asoundrc /etc/asound.conf`

## Turn off LEDs

https://n.ethz.ch/~dbernhard/disable-led-on-a-raspberry-pi.html

```bash
sudo tee "/etc/systemd/system/disable-led.service" > /dev/null <<'EOF'
[Unit]
Description=Disables the power-LED and active-LED
After=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=sh -c "echo 0 | sudo tee /sys/class/leds/PWR/brightness > /dev/null"
ExecStop=sh -c "echo 1 | sudo tee /sys/class/leds/PWR/brightness > /dev/null"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable disable-led.service
sudo systemctl start disable-led.service
```

## Mopidy

https://docs.mopidy.com/en/latest/installation/raspberrypi/#raspberrypi-installation
https://docs.mopidy.com/en/latest/installation/debian/#debian-install
https://docs.mopidy.com/en/latest/running/service/

```bash
sudo mkdir -p /etc/apt/keyrings
sudo wget -q -O /etc/apt/keyrings/mopidy-archive-keyring.gpg \
  https://apt.mopidy.com/mopidy.gpg
sudo wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/bullseye.list
sudo apt update
sudo apt install mopidy

sudo systemctl enable mopidy

sudo apt install python3-pip
sudo python3 -m pip install Mopidy-Iris
sudo sh -c 'echo "mopidy  ALL=NOPASSWD:   /usr/local/lib/python3.9/dist-packages/mopidy_iris/system.sh" >> /etc/sudoers'

# TODO: Move core/cache to a tmpfs/memorylocation

# Web available on all network interfaces
echo "[http]
hostname = ::" | sudo tee -a /etc/mopidy/mopidy.conf

echo "
[file]
media_dirs = /home/fabian/Music" | sudo tee -a /etc/mopidy/mopidy.conf

sudo systemctl restart mopidy
```

### Instal mopidy-spotify

https://github.com/mopidy/mopidy-spotify

```bash
# Confirm with enter
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
sudo apt install libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev gcc pkg-config git
cd ~
git clone --depth 1 https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs
cd gst-plugins-rs
cargo build --package gst-plugin-spotify --release
sudo install -m 644 target/release/libgstspotify.so $(pkg-config --variable=pluginsdir gstreamer-1.0)/
# Verify the plugin is available
gst-inspect-1.0 spotify

sudo python3 -m pip install https://github.com/mopidy/mopidy-spotify/archive/master.zip

# Get client secrets on https://mopidy.com/ext/spotify/#authentication
# credentials from Fabian on 2.7.23
echo "
[spotify]
username = Faebu93
password = DvjNArB37VBRaAkvJpzB
client_id = f576f242-19a4-4d2a-a1ce-f75ed9605289
client_secret = vQ246Z03gOtzWTOMP-v5yPTll0t-0575wO_NSgC22o0=
"| sudo tee -a /etc/mopidy/mopidy.conf

sudo systemctl restart mopidy

# authenticate Iris client and set locales in http://raspberrypi1.home:6680/iris/settings/services/spotify
```

## Snapserver

```bash
# Find latest release on https://github.com/badaix/snapcast/releases
cd ~
wget https://github.com/badaix/snapcast/releases/download/v0.27.0/snapserver_0.27.0-1_armhf.deb
sudo apt install ~/snapserver_0.27.0-1_armhf.deb
sudo pip install websocket-client

# Create and enable loopback ALSA device
#sudo modprobe snd-aloop # probably not card 0 after that, need to reboot
echo "snd-aloop" | sudo tee -a /etc/modules
sudo reboot
# test if it shows up, find number of the loopback device
aplay -l

# configure snapservers inputs
# ampersands had to be escaped
sudo sed -i 's|^source = pipe:///tmp/snapfifo?name=default|# source = pipe:///tmp/snapfifo?name=default \nsource = alsa:///?name=Mopidy 1\&device=hw:0,1,0\&controlscript=meta_mopidy.py|g' /etc/snapserver.conf

# configure Mopidy to output to loopback device
echo "
[audio]
#output = autoaudiosink
output = audioresample ! audioconvert ! audio/x-raw,rate=48000,channels=2,format=S16LE ! alsasink device=hw:0,0,0" | sudo tee -a /etc/mopidy/mopidy.conf

sudo systemctl restart mopidy
sudo systemctl restart snapserver
```

## Snapcast client

TODO: Choose mixer via Snapclient opts, see https://github.com/badaix/snapcast/issues/318#issuecomment-625742834

```bash
# Find latest release on https://github.com/badaix/snapcast/releases
cd ~
wget https://github.com/badaix/snapcast/releases/download/v0.27.0/snapclient_0.27.0-1_without-pulse_armhf.deb
sudo apt install ~/snapclient_0.27.0-1_without-pulse_armhf.deb

# Find name or number of the soundcard with snapclient -l
sudo sed -i 's/SNAPCLIENT_OPTS=""/SNAPCLIENT_OPTS="-s plughw:CARD=IQaudIODAC"/g' /etc/default/snapclient
# TODO: Mixer argument (is default software, maybe HW?)

sudo systemctl restart snapclient
```

## Spotify Connect client

https://github.com/dtcooper/raspotify/wiki/Basic-Setup-Guide

```bash
sudo apt-get -y install curl && curl -sL https://dtcooper.github.io/raspotify/install.sh | sh
```

Configure device name, bitrate etc

```bash
sudo sed -i 's/LIBRESPOT_AUTOPLAY=/#LIBRESPOT_AUTOPLAY=/g' /etc/raspotify/conf
sudo sed -i 's/#LIBRESPOT_NAME="Librespot"/LIBRESPOT_NAME="Stube"/g' /etc/raspotify/conf
sudo sed -i 's/#LIBRESPOT_BITRATE="160"/LIBRESPOT_BITRATE="320"/g' /etc/raspotify/conf
sudo sed -i 's/#LIBRESPOT_DEVICE_TYPE="speaker"/LIBRESPOT_DEVICE_TYPE="avr"/g' /etc/raspotify/conf
sudo sed -i 's/#LIBRESPOT_DEVICE="default"/LIBRESPOT_DEVICE="hw:CARD=E30,DEV=0"/g' /etc/raspotify/conf
sudo sed -i 's/#LIBRESPOT_FORMAT="S16"/LIBRESPOT_FORMAT="S32"/g' /etc/raspotify/conf
echo -e '\n#Use Alsa mixer\nLIBRESPOT_MIXER="alsa"\nLIBRESPOT_ALSA_MIXER_CONTROL="E30 "\nLIBRESPOT_VOLUME_CTRL="linear"\n' | sudo tee -a /etc/raspotify/conf

sudo systemctl restart raspotify
```

## Bluetooth sink

https://github.com/arkq/bluez-alsa/wiki/Installation-from-source

For Mixer control, see https://github.com/arkq/bluez-alsa/blob/master/doc/bluealsa-aplay.1.rst

For commands, see https://scribles.net/controlling-bluetooth-audio-on-raspberry-pi/ for reference

```bash
# Instal dependencies
sudo apt-get -y install git automake build-essential libtool pkg-config python3-docutils
sudo apt-get -y install libasound2-dev libbluetooth-dev libdbus-1-dev libglib2.0-dev libsbc-dev

sudo apt-get -y install libopenaptx-dev bash-completion dbus libasound2 libbluetooth3 libglib2.0-0 libopenaptx0 libsbc1 libspandsp-dev libspandsp2

# Build AAC library
sudo apt-get -y install cmake
cd ~
git clone https://github.com/mstorsjo/fdk-aac.git
cd fdk-aac
./autogen.sh 
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
sudo cmake --install ./
sudo ldconfig

# Build BlueZALSA
cd ~
git clone https://github.com/Arkq/bluez-alsa.git
cd bluez-alsa
autoreconf --install --force
mkdir build
cd build

# create system user for services for additional security
sudo adduser --system --group --no-create-home bluealsa
sudo adduser --system --group --no-create-home bluealsa-aplay
sudo adduser bluealsa-aplay audio
sudo adduser bluealsa bluetooth

../configure --enable-aac --enable-aptx --enable-aptx-hd --with-libopenaptx --enable-msbc --enable-a2dpconf --enable-cli --with-bash-completion --enable-systemd --with-bluealsauser=bluealsa --with-bluealsaaplayuser=bluealsa-aplay
make
sudo make install

# change the options
sudo sh -c "cat >/etc/systemd/system/bluealsa-aplay.service.d/override.conf" << 'EOL'
[Service]
ExecStart=
ExecStart=/usr/bin/bluealsa-aplay -S --pcm=plughw:CARD=E30 --mixer-device=hw:CARD=E30 --mixer-name=E30\x20
EOL
sudo sh -c "cat >/etc/systemd/system/bluealsa.service.d/override.conf" << 'EOL'
[Service]
ExecStart=
ExecStart=/usr/bin/bluealsa -S --keep-alive=5 -p a2dp-sink --a2dp-volume -c AAC -c aptX -c aptX-HD
EOL

sudo systemctl daemon-reload
sudo systemctl enable bluealsa
sudo systemctl enable bluealsa-aplay

# For pairing with a simple pin, use a script of bluez test scripts
#TODO: Doesn't work. Maybe starts too early?
sudo mkdir /opt/bluetooth-pairing
cd /opt/bluetooth-pairing
sudo apt-get -y install bluez-test-scripts
sudo cp /usr/share/doc/bluez-test-scripts/examples/simple-agent fixed-pin-agent
sudo cp /usr/share/doc/bluez-test-scripts/examples/bluezutils.py bluezutils.py
sudo sed -i 's/return ask("Enter PIN Code: ")/return "6353"/g' fixed-pin-agent

sudo apt-get -y install pip
sudo pip install dbus-python
sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev
sudo pip3 install pycairo
sudo pip3 install PyGObject

sudo sh -c "cat >btscript.sh" << 'EOL'
#!/bin/sh
result=`ps aux | grep -i "simple-agent" | grep -v "grep" | wc -l`
if [ $result -ge 0 ]; then
    sudo hciconfig hci0 piscan
    sudo hciconfig hci0 sspmode 0
    sudo /usr/bin/python /opt/bluetooth-pairing/fixed-pin-agent &
else
    echo "BT Agent already started" 
fi
EOL

sudo chmod +x btscript.sh
sudo sed -i 's|exit 0|#Start BT pairing agent\n/opt/bluetooth-pairing/btscript.sh\n\nexit 0|g' /etc/rc.local

sudo reboot
```

## Remote support for Harman Kardon HK970
```bash
# Add IR devices in /boot/config.txt:

echo "dtoverlay=gpio-ir,gpio_pin=26,invert=0,gpio_pull=off,rc-map-name=hk970" | sudo tee -a /boot/config.txt
echo "dtoverlay=gpio-ir-tx,gpio_pin=19" | sudo tee -a /boot/config.txt

sudo apt -y install lirc

# File /etc/lirc/lircd.conf.d/HK970.lirc.conf:
sudo tee "/etc/lirc/lircd.conf.d/HK970.lirc.conf" > /dev/null <<'EOF'
# This config file was automatically generated
# using lirc-0.10.1(default) on Sat Dec 30 15:09:57 2023
# Command line used: -ku --disable-namespace HK970.conf
# Kernel version (uname -r): 6.1.21-v8+
#
# Remote name (as of config file): HK970
# Brand of remote device, the thing you hold in your hand: Harman Kardon
# Remote device model nr: HK970
# Remote device info url:
# Does remote device has a bundled capture device e. g., a
#     usb dongle? : no
#                   Config file was recorded connecting the IR OUT port of the 
#                   receiver to a GPIO pin of a Raspberry Pi 4, adding
#                   dtoverlay=gpio-ir,gpio_pin=26,invert=0,gpio_pull=off
#                   to /boot/config.txt
# Type of device controlled
#     (TV, VCR, Audio, DVD, Satellite, Cable, HTPC, ...) : Receiver/Amp
# Device(s) controlled by this remote:
#     Harman Kardon HK970
#
# The remote used the Extended NEC protocol. While the NEC protocol specifies 
# that the least significant bits of each byte are sent first, the values 
# required by LIRC are most significant bit first within each byte.
# 
# Keys on the remote are labled exactly as their corresponding code label,
# otherwhise the label on the remote is indicated in the comment.
# The RDS key is not recorded, as it has, strangely enough, a different device
# address.

begin remote

  name  HK970
  bits           16
  flags SPACE_ENC
  eps            20
  aeps          200

  header       9000  4500
  one           563  1687
  zero          563   562
  ptrail        563
  repeat       9000  2250
  pre_data_bits  16
  pre_data   0x010E
  gap         46437
  repeat_gap  98187
  min_repeat      0
  toggle_bit_mask 0
  frequency   38000
  duty_cycle     30

      begin codes
          KEY_POWER                0x03FC # POWER ON
          KEY_SLEEP                0xF906 # POWER OFF
          KEY_VOLUMEUP             0xE31C
          KEY_VOLUMEDOWN           0x13EC
          KEY_PLAYPAUSE            0x40BF
          KEY_10CHANNELSDOWN       0x906F # 10+
          KEY_10CHANNELSUP         0x10EF # 10-
          KEY_CD                   0x23DC
          KEY_TUNER                0xC33C
          KEY_TV                   0xCB34
          KEY_TAPE                 0x33CC
          KEY_AUX                  0xA35C
          KEY_MODE                 0x7B84
          KEY_PREVIOUS             0xA05F
          KEY_NEXT                 0x20DF
          KEY_REWIND               0xE01F # Search backwards
          KEY_STOP                 0x807F # Search forward
          KEY_FORWARD              0x609F
          KEY_EJECTCLOSECD         0x00FF # Open/Close
          KEY_MEDIA_REPEAT         0x50AF
          KEY_SHUFFLE              0xB24D # Random
          KEY_SCROLLUP             0x21DE
          KEY_SCROLLDOWN           0xA15E
          KEY_MUTE                 0x837C
          KEY_SELECT               0x15EA
          KEY_0                    0x58A7
          KEY_1                    0x8877
          KEY_2                    0x48B7
          KEY_3                    0xC837
          KEY_4                    0x28D7
          KEY_5                    0xA857
          KEY_6                    0x6897
          KEY_7                    0xE817
          KEY_8                    0x18E7
          KEY_9                    0x9867
          key_PHONO                0x43BC
          key_CDR                  0xAB54
          key_FOLDERUP             0x7887
          key_FOLDERDOWN           0xF807
          key_BAND                 0x817E
          key_FMMODE               0xC936
          key_AUTO                 0x8976
      end codes

end remote
EOF

# Change values in /etc/lirc/lirc_options.conf:
sudo sed -i "s/driver          = devinput/driver          = default/g" /etc/lirc/lirc_options.conf
sudo sed -i "s|device          = auto|device          = /dev/lirc0|g" /etc/lirc/lirc_options.conf

sudo apt install ir-keytable

# add line to /etc/rc_maps.cfg:
echo "*       *                        hk970.toml" | sudo tee -a /etc/rc_maps.cfg

# File /etc/rc_keymaps/hk970.toml:
sudo tee "/etc/rc_keymaps/hk970.toml" > /dev/null <<'EOF'
[[protocols]]
name = "HK970"
protocol = "nec"
variant = "necx"
[protocols.scancodes]
0x8070C0 = "KEY_POWER"
0x80709F = "KEY_SLEEP"
0x8070C7 = "KEY_VOLUMEUP"
0x8070C8 = "KEY_VOLUMEDOWN"
0x807002 = "KEY_PLAYPAUSE"
0x807009 = "KEY_10CHANNELSDOWN"
0x807008 = "KEY_10CHANNELSUP"
0x8070C4 = "KEY_CD"
0x8070C3 = "KEY_TUNER"
0x8070D3 = "KEY_TV"
0x8070CC = "KEY_TAPE"
0x8070C5 = "KEY_AUX"
0x8070DE = "KEY_MODE"
0x807005 = "KEY_PREVIOUS"
0x807004 = "KEY_NEXT"
0x807007 = "KEY_REWIND"
0x807001 = "KEY_STOP"
0x807006 = "KEY_FORWARD"
0x807000 = "KEY_EJECTCLOSECD"
0x80700A = "KEY_MEDIA_REPEAT"
0x80704D = "KEY_SHUFFLE"
0x807084 = "KEY_SCROLLUP"
0x807085 = "KEY_SCROLLDOWN"
0x8070C1 = "KEY_MUTE"
0x8070A8 = "KEY_SELECT"
0x80701A = "KEY_0"
0x807011 = "KEY_1"
0x807012 = "KEY_2"
0x807013 = "KEY_3"
0x807014 = "KEY_4"
0x807015 = "KEY_5"
0x807016 = "KEY_6"
0x807017 = "KEY_7"
0x807018 = "KEY_8"
0x807019 = "KEY_9"
EOF
```