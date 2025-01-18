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
Installing on a Raspberry Pi OS Lite 64-bit (Released 2023-05-03)

First find desired audio output: `cat /proc/asound/card*/id`

Set default audio output to the desired one (#TODO: test command): `sudo sed -i 's/card 0/card E30/g' ~/.asoundrc` - file needs to be created first, e. g. by setting the sound output with `sudo raspi-config`, maybe better to set name of soundcard instead of number, document how to find this

Link sound configuration to default/root configuration: `sudo ln -s ~/.asoundrc /etc/asound.conf`

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
sudo tee -a /boot/firmware/config.txt > /dev/null <<'EOF'
[all]
dtoverlay=gpio-fan,gpiopin=18,temp=80000
EOF
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

First find desired audio output: `cat /proc/asound/card*/id`

Set default audio output to the desired one (#TODO: test command): `sudo sed -i 's/card 0/card E30/g' ~/.asoundrc` - file needs to be created first, e. g. by setting the sound output with `sudo raspi-config`, maybe better to set name of soundcard instead of number, document how to find this

Link sound configuration to default/root configuration: `sudo ln -s ~/.asoundrc /etc/asound.conf`

## Snapcast client

TODO: Choose mixer via Snapclient opts, see https://github.com/badaix/snapcast/issues/318#issuecomment-625742834

```bash
# Find latest release on https://github.com/badaix/snapcast/releases
# might want to install the arm64 package dowloaded in the snapserver step instead
cd ~
#wget https://github.com/badaix/snapcast/releases/download/v0.27.0/snapclient_0.27.0-1_without-pulse_armhf.deb
sudo apt install ~/snapclient_0.27.0-1_without-pulse_arm64.deb

# Find name or number of the soundcard with snapclient -l
sudo sed -i 's/SNAPCLIENT_OPTS=""/SNAPCLIENT_OPTS="--soundcard plughw:CARD=IQaudIODAC"/g' /etc/default/snapclient
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

sudo apt -y install lirc

sudo install ./audio-client/HK970.lirc.conf /etc/lirc/lircd.conf.d
# Change values in /etc/lirc/lirc_options.conf:
sudo sed -i "s/driver          = devinput/driver          = default/g" /etc/lirc/lirc_options.conf
sudo sed -i "s|device          = auto|device          = /dev/lirc0|g" /etc/lirc/lirc_options.conf

sudo apt install ir-keytable

# add line to /etc/rc_maps.cfg:
echo "*       *                        hk970.toml" | sudo tee -a /etc/rc_maps.cfg

sudo install ./audio-client/hk970.toml /etc/rc_keymaps
```


Commands that may or may not help in finding and testing those keymaps:

```bash
sudo evtest
sudo irsend -# 11 SEND_ONCE HK970 KEY_VOLUMEUP
```

## Python script controlling output devices

Install dependencies.
Could also avoid depending on python lirc by using system calls instead
```bash
sudo apt install -y python3-pip

cd OutputDeviceController
python3 -m venv .venv
source .venv/bin/activate
pip install lirc
```