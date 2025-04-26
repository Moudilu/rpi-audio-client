# Raspberry Pi Audio Client Installation notes

## Requirements

For Spotify Connect to work, mDNS is required to discover the Spotify Connect clients in your network. This requires IP multicast to work, which is [poorly supported on some Wifi routers](https://superuser.com/a/733115). If either your Raspberry Pis or your clients wanting to play via Spotify Connect, make sure your router supports and is properly configured to route multicast packets to wireless clients.

Experiences with some routers:

- Asus RT-AX92U: Discovery was sometimes working, sometimes not with default settings. Currently set Wireless > Professional > Multicast Rate(Mbps) to `OFDM 12` for all available bands.

## System setup

Installing on a Raspberry Pi OS Lite 64-bit

Update with

```bash
sudo apt update
sudo apt upgrade
```

Clone this repository with

```bash
sudo apt install -y git
git clone https://github.com/Moudilu/rpi-audio-client.git
cd rpi-audio-client
```

Some of the following commands assume that you are in the folder `rpi-audio-client`.

### Disable passwordless sudo

```bash
sudo rm /etc/sudoers.d/010_pi-nopasswd
```


### Enable automatic upgrades

```bash
sudo apt install -y unattended-upgrades
sudo tee /etc/apt/apt.conf.d/60UnattendedUpgradesUser << 'EOF'
Unattended-Upgrade::Origins-Pattern {
    "origin=Raspberry Pi Foundation,codename=${distro_codename}";
    "codename=raspotify";
    // "origin=Debian Backports,codename=${distro_condename}-backports,label=Debian Backports"; // don't automatically update packages from backports, has to be done manually for improved stability
}
EOF
```

### Set hostname

Set the name of your device with the following command. It will be used to identify it with e.g. Spotify, Snapcast or Bluetooth. No format restrictions apply, appropriate reformatting will automatically be done.

```bash
read -p "Enter desired hostname: " HOSTNAME
sudo hostnamectl hostname "$HOSTNAME"
sudo hostnamectl --pretty hostname "$HOSTNAME"
```

### Turn off LEDs

https://n.ethz.ch/~dbernhard/disable-led-on-a-raspberry-pi.html

```bash
sudo install ./audio-client/disable-led.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable disable-led.service
sudo systemctl start disable-led.service
```

### Enable the fan

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

### Install Prometheus exporter

If you want and have a Prometheus instance running elsewhere, you can install an exporter on this machine to monitor it.

```bash
sudo apt install --no-install-recommends prometheus-node-exporter
# Add additional collectors to node exporter
sudo sed -i 's/ARGS="/ARGS="--collector.systemd /' /etc/default/prometheus-node-exporter
sudo systemctl restart prometheus-node-exporter
```

Then, in the Prometheus config of your monitoring instance, add something like the following lines to the `scrape_configs` and reload the config of the Prometheus service:

```yaml
  - job_name: "node <name of your Pi>"
    static_configs:
      - targets: ['<hostname or IP of your Pi>:9100']
```

### Install Pipewire

Install the Pipewire Audio server

```bash
# In Debian Bookworm only version 0.4.13 was available as of March 2025. Install 0.5.8 from Backports repository
# pipewire-pulse not needed so far
source /etc/os-release
echo "deb http://deb.debian.org/debian $VERSION_CODENAME-backports main" | sudo tee /etc/apt/sources.list.d/backports.list
sudo apt update
sudo apt install -y -t $VERSION_CODENAME-backports wireplumber wireplumber-doc pipewire-alsa libspa-0.2-bluetooth
systemctl --user stop pipewire.service pipewire.socket
sudo systemctl --user --global mask pipewire.service pipewire.socket

# Install the system service files for pipewire
PIPEWIRE_VERSION=$(pipewire --version | grep Compiled | sed 's/.* //')
WIREPLUMBER_VERSION=$(wireplumber --version | grep Compiled | sed 's/.* //')
echo "Getting system-wide service files for pipewire version '${PIPEWIRE_VERSION}' and wireplumber version '${WIREPLUMBER_VERSION}'"
sudo curl https://gitlab.freedesktop.org/pipewire/pipewire/-/raw/${PIPEWIRE_VERSION}/src/daemon/systemd/system/pipewire.socket -o /etc/systemd/system/pipewire.socket
sudo curl https://gitlab.freedesktop.org/pipewire/pipewire/-/raw/${PIPEWIRE_VERSION}/src/daemon/systemd/system/pipewire-manager.socket -o /etc/systemd/system/pipewire-manager.socket
curl https://gitlab.freedesktop.org/pipewire/pipewire/-/raw/${PIPEWIRE_VERSION}/src/daemon/systemd/system/pipewire.service.in | sed "s|@PW_BINARY@|$(which pipewire)|g" | sudo tee /etc/systemd/system/pipewire.service > /dev/null
curl https://gitlab.freedesktop.org/pipewire/wireplumber/-/raw/${WIREPLUMBER_VERSION}/src/systemd/system/wireplumber.service.in | sed "s|@WP_BINARY@|$(which wireplumber)|g" | sudo tee /etc/systemd/system/wireplumber.service > /dev/null

# Create user and make it use the system D-Bus
sudo adduser --system --home /var/lib/pipewire --group pipewire
sudo usermod -a -G audio pipewire
# The normal user shall be allowed to play sound
sudo usermod -a -G pipewire $(whoami)
sudo install -d /etc/systemd/system/pipewire.service.d
sudo tee /etc/systemd/system/pipewire.service.d/10-dbus.conf > /dev/null << EOF
[Service]
# Use the system bus instead of a session bus, which is not running
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
EOF
sudo install -d /etc/systemd/system/wireplumber.service.d
sudo cp /etc/systemd/system/pipewire.service.d/10-dbus.conf /etc/systemd/system/wireplumber.service.d/10-dbus.conf
sudo tee /etc/systemd/system/wireplumber.service.d/20-profile.conf > /dev/null << EOF
[Service]
# Use the embedded profile, which does not store state but loads some system defaults at boot
ExecStart=
ExecStart=/usr/bin/wireplumber -p main-embedded-audio
EOF
sudo systemctl daemon-reload

# Configure wireplumber and set the default node
sudo install -Dt /etc/wireplumber/wireplumber.conf.d audio-client/80-main-embedded-audio.conf audio-client/60-device-settings.conf

# Try to infer the default audio device. If there is only one other active node than the default headphones output, it probably is the one.
DEFAULT_NODE=$(pw-dump | jq '.[].info.props."node.nick" | select(. != null)' | grep -v bcm2835)
if [[ "$(echo "${DEFAULT_NODE}" | wc -l)" -ne 1 ]]; then
echo "More than one possible default nodes"
echo "Available nodes:"
echo "${DEFAULT_NODE}"
echo
read -p "Enter default node: " DEFAULT_NODE
fi

# Remove potential leading and trailing quotes
DEFAULT_NODE="$(sed -e 's/^"//' -e 's/"$//' <<<"${DEFAULT_NODE}")"

echo "Setting \"${DEFAULT_NODE}\" as default output node"

DEFAULT_NODE="${DEFAULT_NODE}" envsubst < audio-client/90-default-output-node.conf | sudo tee /etc/wireplumber/wireplumber.conf.d/90-default-output-node.conf > /dev/null

sudo systemctl enable --now pipewire.socket pipewire-manager.socket pipewire.service wireplumber.service
```

TODO:
- Set default volume -> https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/settings.html "device.routes.default-sink-volume"
- Use hardware volume control instead of soft volume -> already set api.alsa.soft-mixer in 90-default-output-node.conf - does it have the desired effect?
- Make it use all framerates the HW supports -> https://docs.pipewire.org/page_man_pipewire_conf_5.html "default.clock.allowed-rates"

## Install audio clients

### Snapcast client

TODO: Choose mixer via Snapclient opts, see https://github.com/badaix/snapcast/issues/318#issuecomment-625742834

```bash
# Get the newer version from the backports repo
source /etc/os-release
sudo apt install -y -t $VERSION_CODENAME-backports snapclient

# Find name or number of the soundcard with snapclient -l
echo "SNAPCLIENT_OPTS=\"--host 192.168.0.20 \"" | sudo tee /etc/default/snapclient
# TODO: Mixer argument (is default software, maybe HW?)

sudo mkdir -p /etc/systemd/system/snapclient.service.d
sudo tee /etc/systemd/system/snapclient.service.d/20-pipewire.conf > /dev/null << EOF
[Service]
SupplementaryGroups=pipewire
EOF
sudo systemctl daemon-reload
sudo systemctl restart snapclient
```

### Spotify Connect client

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
#LIBRESPOT_DEVICE="plughw:CARD=${DEVICE}"
LIBRESPOT_FORMAT="S32"
#Use Alsa Mixer
#LIBRESPOT_MIXER="alsa"
#LIBRESPOT_ALSA_MIXER_CONTROL="${DEVICE}"
#LIBRESPOT_VOLUME_CTRL="linear"
EOF
sudo mkdir -p /etc/systemd/system/raspotify.service.d
sudo tee /etc/systemd/system/raspotify.service.d/20-pipewire.conf > /dev/null << EOF
[Service]
SupplementaryGroups=pipewire
EOF
sudo systemctl daemon-reload
sudo systemctl restart raspotify
```

### Bluetooth sink

Pipewire supports being a BT sink out of the box. Pairing is implemented through the audio_controller script installed below.

To manually connect devices, https://github.com/arkq/bluez-alsa/wiki/Bluetooth-Pairing-And-Connecting#bluealsa-host-as-responder might help.

In case pairing fails, the device possibly is in some half-registered state.
In that case, the following command might help: `bluetoothctl`, then enter
`devices` to see all registered devices, then `remove <device>` for the
concerned device. After that, retry pairing.
  
Possibly helps with mpris for bluetooth clients: <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/test/example-player>


### Remote support for Harman Kardon HK970

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

sudo apt install -y ir-keytable

# add line to /etc/rc_maps.cfg:
echo "*       *                        hk970.toml" | sudo tee -a /etc/rc_maps.cfg

sudo install ./audio-client/hk970.toml /etc/rc_keymaps

sudo reboot
```

Commands that may or may not help in finding and testing those keymaps:

```bash
sudo apt install -y evtest
evtest
irsend -# 11 SEND_ONCE HK970 KEY_VOLUMEUP
```

### Python script controlling output devices

Install https://github.com/Moudilu/audio_controller as per the instructions of the project.

```bash
sudo apt install -y pipx python3-dev
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install git+https://github.com/Moudilu/audio_controller.git
sudo useradd -r audio-controller
sudo wget -O /etc/systemd/system/audio-controller.service https://github.com/Moudilu/audio_controller/raw/refs/heads/main/resources/audio-controller.service
sudo systemctl daemon-reload
sudo systemctl enable --now audio-controller
```

To update the audio-controller project, run `sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx upgrade git+https://github.com/Moudilu/audio_controller.git` or `sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx upgrade-all` to upgrade any global pipx packages.