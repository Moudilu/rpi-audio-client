# Mopidy and Snapcast server

## Instructions for installing on x86 server with docker

```bash
git clone https://github.com/Faebu93/rpi-audio-client.git
cd rpi-audio-client
```

## Install service

```bash
sudo install -D -t /etc/sound-server ./sound-server/mopidy.conf ./sound-server/snapserver.conf ./sound-server/compose.yml ./sound-server/beets-config.yaml
sudo install -d /var/lib/sound-server/beets
sudo install -m 644 ./sound-server/sound-server.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable sound-server
sudo systemctl start sound-server
```

In case you have nftables configured, you need to open some ports. For a [Private cloud](https://github.com/Faebu93/Private-Cloud) server:

```bash
sudo install -m 600 ./sound-server/30-sound-server.rules /etc/inet-filter.rules.d
sudo systemctl reload nftables
```