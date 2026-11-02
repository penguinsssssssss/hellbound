# Hellbound

A Slack bot that screams about how it's going to hell, on a timer. It posts one of
~27 messages to a channel every hour (± 15 min), going through all of them in a
shuffled order before repeating any. Standard library only, nothing to install.

```bash
python3 hellbound.py                          # every 60 ± 15 min, forever
python3 hellbound.py --every 30 --jitter 5    # every 25–35 min
python3 hellbound.py --once                   # one scream, then exit
python3 hellbound.py --dry-run --every 0.05 --jitter 0   # print to the terminal, no Slack
```

Add or edit lines in `MESSAGES` at the top of `hellbound.py`. `{time}` and `{day}`
are filled in when a message is sent.

## Setup (once)

1. https://api.slack.com/apps → **Create New App → From a manifest** → pick the
   workspace → paste `manifest.yml`.
2. Optional: **Basic Information → Display Information** → upload a profile picture.
3. **Install App → Install to Workspace** (the workspace may need an admin to
   approve). Copy the **Bot User OAuth Token**. That's `SLACK_BOT_TOKEN` (`xoxb-…`).
4. `cp .env.example .env` and fill in the token and `SLACK_CHANNEL`, the channel to
   scream in. With `chat:write.public` it can post in any public channel without being
   invited. For a private channel, `/invite @Hellbound` there first.

## Keeping it running

It only screams while the script is running. `deploy/install.sh` makes it a systemd
service that starts on boot and restarts if it crashes. Arguments go to the script:

```bash
sh deploy/install.sh --every 0.3333 --jitter 0   # every 20 s
journalctl -u hellbound -f                     # watch it
sudo systemctl disable --now hellbound         # make it stop
```

On a Raspberry Pi or server, that's it: it runs whether your laptop is on or not.
In WSL (needs `systemd=true` in `/etc/wsl.conf`), it runs only while WSL is up, and
Windows shuts WSL down a little while after the last WSL window closes. Keep a WSL
terminal open, or have Windows start one hidden at logon.

## More than one bot

The bot's name and picture live in its Slack app, not in this code, so one checkout
can run several differently named bots. For each one:

1. Create another Slack app from `manifest.yml`, changing `name` and `display_name`
   in the manifest editor before you click Create. Install it and copy its token.
2. Put its token and channel in `.env.NAME` (e.g. `.env.second`), with `NAME` in
   lowercase letters, digits, and `-`. Every `.env.*` except the example is gitignored.
3. `sh deploy/install.sh --instance NAME --every 0.3333 --jitter 0`. This installs a
   separate `hellbound-NAME` service, so `journalctl -u hellbound-NAME -f` and
   `sudo systemctl disable --now hellbound-NAME` work on that bot alone.

After editing `MESSAGES`, restart every bot: `sudo systemctl restart 'hellbound*'`.

## Errors

Network failures are logged and retried at the next scream. A bad token, missing
scope, or unknown channel stops the script with the reason.
