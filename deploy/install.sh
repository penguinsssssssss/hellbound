#!/bin/sh
# Set up Hellbound as an always-on systemd service on a Raspberry Pi,
# WSL with systemd, or any systemd Linux box. Run from the project folder as your
# normal user; any other arguments are passed to hellbound.py:
#   sh deploy/install.sh                          # every 60 +/- 15 min
#   sh deploy/install.sh --every 0.3333 --jitter 0   # every 20 s
#   sh deploy/install.sh --instance NAME ...      # another bot: .env.NAME, hellbound-NAME
# Re-running is safe; it replaces the unit file and restarts the service.
set -eu

dir=$(pwd)
user=$(id -un)
unit=hellbound
env=.env
if [ "${1:-}" = --instance ]; then
    case "${2:-}" in
        "" | *[!a-z0-9-]*) echo "--instance needs a name of lowercase letters, digits, and -"; exit 1 ;;
    esac
    unit=hellbound-$2
    env=.env.$2
    shift 2
fi
[ -f hellbound.py ] || { echo "run this from the Hellbound folder"; exit 1; }
[ -f "$env" ] || { echo "create $env with SLACK_BOT_TOKEN and SLACK_CHANNEL first"; exit 1; }
chmod 600 "$env"

sed -e "s|User=pi|User=$user|" -e "s|/home/pi/Hellbound|$dir|g" \
    -e "s|^Description=.*|& ($unit)|" \
    -e "s|hellbound.py$|hellbound.py --env-file $env $*|" deploy/hellbound.service \
    | sudo tee "/etc/systemd/system/$unit.service" >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable "$unit.service"
sudo systemctl restart "$unit.service"

echo
systemctl --no-pager --lines=5 status "$unit.service" || true
echo
echo "logs: journalctl -u $unit -f"
echo "stop: sudo systemctl disable --now $unit"
