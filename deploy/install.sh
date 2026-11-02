#!/bin/sh
# Set up Hellbound as an always-on systemd service on a Raspberry Pi,
# WSL with systemd, or any systemd Linux box. Run from the project folder as your
# normal user; any arguments are passed to hellbound.py:
#   sh deploy/install.sh                          # every 60 +/- 15 min
#   sh deploy/install.sh --every 0.3333 --jitter 0   # every 20 s
# Re-running is safe; it replaces the unit file and restarts the service.
set -eu

dir=$(pwd)
user=$(id -un)
[ -f hellbound.py ] || { echo "run this from the Hellbound folder"; exit 1; }
[ -f .env ] || { echo "create .env with SLACK_BOT_TOKEN and SLACK_CHANNEL first"; exit 1; }
chmod 600 .env

sed -e "s|User=pi|User=$user|" -e "s|/home/pi/Hellbound|$dir|g" \
    -e "s|hellbound.py$|hellbound.py $*|" deploy/hellbound.service \
    | sudo tee /etc/systemd/system/hellbound.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable hellbound.service
sudo systemctl restart hellbound.service

echo
systemctl --no-pager --lines=5 status hellbound.service || true
echo
echo "logs: journalctl -u hellbound -f"
echo "stop: sudo systemctl disable --now hellbound"
