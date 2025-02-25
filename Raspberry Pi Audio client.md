# Raspberry Pi Audio Client Installation notes

Installing on a Raspberry Pi OS Lite 64-bit

Update with

```bash
sudo apt update
sudo apt upgrade
```

Clone this repository with

```bash
sudo apt install git
git clone https://github.com/Faebu93/rpi-audio-client.git
cd rpi-audio-client
```

Some of the following commands assume that you are in the folder `rpi-audio-client`.

## Disable passwordless sudo

```bash
sudo rm /etc/sudoers.d/010_pi-nopasswd
```

## Set hostname

Set the name of your device with the following command. It will be used to identify it with e.g. Spotify, Snapcast or Bluetooth. No format restrictions apply, appropriate reformatting will automatically be done.

```bash
read -p "Enter desired hostname: " HOSTNAME
sudo hostnamectl hostname "$HOSTNAME"
sudo hostnamectl --pretty hostname "$HOSTNAME"
```

## Turn off LEDs

https://n.ethz.ch/~dbernhard/disable-led-on-a-raspberry-pi.html

```bash
sudo install ./audio-client/disable-led.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable disable-led.service
sudo systemctl start disable-led.service
```

## Enable the fan

This enables the fan on pin 18 when temperature exceeds 80°C.

```bash
echo "dtoverlay=gpio-fan,gpiopin=18,temp=80000" | sudo tee -a /boot/firmware/config.txt
```

Connect the fan like this:

```
                   +5V                                                  
                    ^                                                   
                    |                                                   
                   .-.                                                  
                  ( X )                                                 
                   '-'                                                  
                    |                                                   
                    |                                                   
            ___   |/                                                    
   Pin 18 -|___|--|  NPN General Purpose transistor                     
            500R  |>                                                    
                    |                                                   
                   GND
                                   
(created by AACircuit.py © 2020 JvO) 
```

## Set default ALSA output

Set the default sound card:

```bash
echo "Find the name of the desired default audio device"
cat /proc/asound/card*/id
read -p "Enter the name of your default sound card:" DEVICE
cat ./audio-client/.asoundrc | DEVICE=$DEVICE envsubst > ~/.asoundrc
# Link sound configuration to default/root configuration
sudo ln -s ~/.asoundrc /etc/asound.conf
```

Check and set the volume to 100% with `alsamixer`.

## Snapcast client

TODO: Choose mixer via Snapclient opts, see https://github.com/badaix/snapcast/issues/318#issuecomment-625742834

```bash
# Activate the debian backports repository, to get a newer version of snapcast
source /etc/os-release
echo "deb http://deb.debian.org/debian $VERSION_CODENAME-backports main" | sudo tee /etc/apt/sources.list.d/backports.list
sudo apt update

sudo apt install -t $VERSION_CODENAME-backports snapclient

# Find name or number of the soundcard with snapclient -l
echo "SNAPCLIENT_OPTS=\"--soundcard plughw:CARD=$DEVICE --host 192.168.0.20\"" | sudo tee /etc/default/snapclient
# TODO: Mixer argument (is default software, maybe HW?)

sudo systemctl restart snapclient
```

## Spotify Connect client

https://github.com/dtcooper/raspotify/wiki/Basic-Setup-Guide

```bash
sudo apt-get -y install curl && curl -sL https://dtcooper.github.io/raspotify/install.sh | sh
```

Configure device name, bitrate etc. Should be run only once. Otherwhise exit the file manually, removing the last bit.

```bash
sudo tee -a /etc/raspotify/conf << EOF

# Custom settings
LIBRESPOT_AUTOPLAY=off
LIBRESPOT_NAME="$(hostnamectl --pretty)"
LIBRESPOT_BITRATE="320"
LIBRESPOT_DEVICE_TYPE="avr"
LIBRESPOT_DEVICE="plughw:CARD=${DEVICE}"
LIBRESPOT_FORMAT="S32"
#Use Alsa Mixer
#LIBRESPOT_MIXER="alsa"
#LIBRESPOT_ALSA_MIXER_CONTROL="${DEVICE}"
#LIBRESPOT_VOLUME_CTRL="linear"
EOF

sudo systemctl restart raspotify
```

## Bluetooth sink

Add service to play audio via bluetooth.

```bash
sudo apt install libasound2-plugin-bluez bluez-alsa-utils
sudo mkdir -p /etc/systemd/system/bluealsa-aplay.service.d
sudo tee /etc/systemd/system/bluealsa-aplay.service.d/override.conf << EOF
[Service]
ExecStart=
ExecStart=/usr/bin/bluealsa-aplay --pcm=plughw:CARD=${DEVICE} --mixer-device=hw:CARD=${DEVICE} --mixer-name=${DEVICE}

EOF
sudo mkdir -p /etc/systemd/system/bluealsa.service.d
sudo tee /etc/systemd/system/bluealsa.service.d/override.conf << EOF
[Service]
ExecStart=
ExecStart=/usr/bin/bluealsa --keep-alive=5 -p a2dp-sink --a2dp-volume

EOF

sudo systemctl daemon-reload
sudo systemctl restart bluealsa
sudo systemctl restart bluealsa-aplay
```

Now, phones can be connected according to https://github.com/arkq/bluez-alsa/wiki/Bluetooth-Pairing-And-Connecting#bluealsa-host-as-responder, it should be possible to stream media. Maybe reboot needed.

  
Possibly helps with mpris: <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/test/example-player>

## Enable automatic upgrades

```bash
sudo apt install unattended-upgrades
sudo tee /etc/apt/apt.conf.d/60UnattendedUpgardesUser << 'EOF'
Unattended-Upgrade::Origins-Pattern {
    "origin=Raspberry Pi Foundation,codename=${distro_codename}";
    "codename=raspotify"
}
EOF
```

## Remote support for Harman Kardon HK970

Wire up the IR 3.5mm in-/output of the receiver as follows:

```
                ___                                                     
AVR INPUT  o---|___|-o RPi Pin 5                                         
                100R                                                    
AVR OUTPUT o-                                                           
            |                                                           
           .-.                                                          
           | |                                                          
           | |1K                                                        
           '-'                                                          
            |                                                           
            +--------o RPi Pin 25                                        
           .-.                                                          
           | |                                                          
           | |1K                                                        
           '-'                                                          
            |   ___                                                     
AVR GND   o-+--|___|-o RPi GND                                           
                33R                                      

(created by AACircuit.py © 2020 JvO)               
```

```bash
# Add IR devices in config.txt:
echo "dtoverlay=gpio-ir,gpio_pin=25,invert=0,gpio_pull=off,rc-map-name=hk970" | sudo tee -a /boot/firmware/config.txt
echo "dtoverlay=gpio-ir-tx,gpio_pin=5" | sudo tee -a /boot/firmware/config.txt

# Power key shall not trigger a shutdown
sudo install -D -t /etc/systemd/logind.conf.d ./audio-client/60-disable-powerkey.conf 

sudo apt -y install lirc

sudo install ./audio-client/HK970.lirc.conf /etc/lirc/lircd.conf.d
# Change values in /etc/lirc/lirc_options.conf:
sudo sed -i "s/driver          = devinput/driver          = default/g" /etc/lirc/lirc_options.conf
sudo sed -i "s|device          = auto|device          = /dev/lirc0|g" /etc/lirc/lirc_options.conf

sudo apt install ir-keytable

# add line to /etc/rc_maps.cfg:
echo "*       *                        hk970.toml" | sudo tee -a /etc/rc_maps.cfg

sudo install ./audio-client/hk970.toml /etc/rc_keymaps

sudo reboot
```

Commands that may or may not help in finding and testing those keymaps:

```bash
sudo apt install evtest
evtest
irsend -# 11 SEND_ONCE HK970 KEY_VOLUMEUP
```

## Python script controlling output devices

Install https://github.com/Moudilu/audio_controller as per the instructions of the project.

```bash
sudo apt install pipx
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install git+https://github.com/Moudilu/audio_controller.git
sudo useradd -r audio-controller
sudo wget -O /etc/systemd/system/audio-controller.service https://github.com/Moudilu/audio_controller/raw/refs/heads/main/resources/audio-controller.service
sudo systemctl daemon-reload
sudo systemctl enable --now audio-controller
```

To update the audio-controller project, run `sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx upgrade git+https://github.com/Moudilu/audio_controller.git` or `sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx upgrade-all` to upgrade any global pipx packages.