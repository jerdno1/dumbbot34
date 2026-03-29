# Discord Booru Bot -- Setup Guide

## Commands

Prefix is `.` by default, but can be changed via the `BOT_PREFIX` environment variable.

| Command | Aliases | Description |
|---|---|---|
| `.random [tags]` | `.rand`, `.r` | Browse posts in random order |
| `.top [tags]` | `.best`, `.highest` | Browse posts, highest score first |
| `.bottom [tags]` | `.worst`, `.lowest`, `.flop` | Browse posts, lowest score first |
| `.date [tags]` | `.new`, `.newest`, `.recent` | Browse posts, newest first |
| `.favs` | `.favourites`, `.favorites`, `.faves` | Browse this server's favourited posts |
| `.meme` | | Random meme from Reddit |
| `.ping` | | Check bot latency |
| `.help` | | List all commands |

### Tag filtering

Tags can be passed directly after any booru command. Prefix a tag with `-` to exclude it.

```
.random cat green_shirt -blue_shirt
.top solo -rating:explicit
```

---

## Step 1 -- Create a Discord Application & Bot

1. Go to https://discord.com/developers/applications
2. Click **New Application**, give it a name, click Create
3. Go to the **Bot** tab on the left
4. Click **Add Bot** -- confirm
5. Under **Token**, click **Reset Token** and copy it somewhere safe (you will need it later)
6. Scroll down and enable these **Privileged Gateway Intents**:
   - Message Content Intent
7. Click **Save Changes**

## Step 2 -- Invite the Bot to Your Server

1. Go to the **OAuth2 > URL Generator** tab
2. Under **Scopes**, check: `bot`
3. Under **Bot Permissions**, check: `Send Messages`, `Embed Links`, `Read Message History`
4. Copy the generated URL at the bottom and open it in your browser
5. Select your server and authorize

## Step 3 -- Deploy to Railway (Free Hosting)

1. Make a GitHub account if you don't have one: https://github.com
2. Create a new repository (can be private) and upload all the bot files:
   - `bot.py`
   - `requirements.txt`
   - `railway.toml`
3. Go to https://railway.app and sign up with your GitHub account
4. Click **New Project > Deploy from GitHub repo**
5. Select your repository
6. Once it starts deploying, click on the service, then go to **Variables**
7. Add the following variables:

| Name | Value |
|---|---|
| `DISCORD_TOKEN` | Your bot token from Step 1 |
| `BOT_PREFIX` | Command prefix (default: `.`) |
| `BOORU_USER_ID` | (Optional) rule34 user ID for API auth |
| `BOORU_API_KEY` | (Optional) rule34 API key for API auth |

8. Click **Deploy** -- done!

Railway gives you $5 free credits per month. A bot like this uses roughly $0.50-1/month, so you're well within free limits.

## Local Testing (Optional)

If you want to test locally before deploying:

```bash
pip install -r requirements.txt

# Windows
set DISCORD_TOKEN=your_token_here
set BOT_PREFIX=.

# Mac/Linux
export DISCORD_TOKEN=your_token_here
export BOT_PREFIX=.

python bot.py
```
