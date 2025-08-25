# CVRGU ClassBot – Replit (Free 24/7 via ping)
This is a **Replit-ready** Telegram bot using **polling** and a tiny Flask server so you can ping it (e.g., with UptimeRobot) to keep it awake on the free tier.

## Setup on Replit
1. Create a new **Python** Repl and **Upload** these files.
2. Open **Tools → Secrets** and add:
   - `TELEGRAM_BOT_TOKEN` = your (fresh) BotFather token
3. Click **Run**. The Repl console will show a **web URL** like `https://<repl>.<user>.repl.co/`.

> IMPORTANT: If your token was ever shared publicly, regenerate it in @BotFather for safety.

## Keep it 24/7 (free)
- Go to **uptimerobot.com** → Add **HTTP(s) monitor** → URL = your Replit web URL (root `/`). Set interval to 5 minutes.
- As long as it is pinged periodically, the process stays alive and your bot keeps polling Telegram.

## Test
- In Telegram, open your bot and send `/start` or press **Where is the class?**

## Files
- `bot_core.py` – timetable, handlers, buttons, reminders
- `keep_alive.py` – tiny Flask web server for uptime pings
- `main.py` – starts keep_alive and the bot (polling)
- `requirements.txt` – libs
- `.replit` – run command

## Notes
- The Flask server listens on env `PORT` (Replit sets this).
- If your Repl still sleeps, confirm pings are hitting the URL and the **Run** button says “Running”.

Stay safe: never commit your token to public code.
