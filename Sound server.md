# Mopidy and Snapcast server

## Instructions for installing on x86 server with docker

```bash
git clone https://github.com/Faebu93/rpi-audio-client.git
cd rpi-audio-client
```

## Install service

```bash
sudo install -D -m 644 -t /etc/sound-server ./sound-server/compose.yml
sudo install -m 644 ./sound-server/sound-server.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable sound-server
sudo systemctl start sound-server
```
