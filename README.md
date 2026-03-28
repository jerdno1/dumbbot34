# Discord Fun Bot -- Setup Guide

## Commands

| Command | Description |
|---|---|
| `/meme` | Random meme from Reddit (memes, dankmemes, me_irl, etc.) |
| `/8ball <question>` | Ask the magic 8-ball |
| `/fortune` | Get your fortune for the day |
| `/trivia` | Start a 30-second trivia question in chat |
| `/coinflip` | Flip a coin |
| `/roll [sides]` | Roll a dice (d4/d6/d8/d10/d12/d20/d100) |
| `/ping` | Check bot latency |

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
2. Under **Scopes**, check: `bot` and `applications.commands`
3. Under **Bot Permissions**, check: `Send Messages`, `Embed Links`, `Read Message History`
4. Copy the generated URL at the bottom and open it in your browser
5. Select your server and authorize

## Step 3 -- Deploy to Railway (Free Hosting)

1. Make a GitHub account if you don't have one: https://github.com
2. Create a new repository (can be private) and upload all the bot files:
   - bot.py
   - requirements.txt
   - railway.toml
3. Go to https://railway.app and sign up with your GitHub account
4. Click **New Project > Deploy from GitHub repo**
5. Select your repository
6. Once it starts deploying, click on the service, then go to **Variables**
7. Add a new variable:
   - Name: `DISCORD_TOKEN`
   - Value: (paste your bot token from Step 1)
8. Click **Deploy** -- done!

Railway gives you $5 free credits per month. A bot like this uses roughly $0.50-1/month, so you're well within free limits.

## Local Testing (Optional)

If you want to test locally before deploying:

```bash
pip install -r requirements.txt
set DISCORD_TOKEN=your_token_here   # Windows
export DISCORD_TOKEN=your_token_here  # Mac/Linux
python bot.py
```

## Adding More Trivia Questions

Open `bot.py` and find the `TRIVIA` list near the top. Add more questions in this format:

```python
{"q": "Your question here?", "a": "answer"},
```

The answer check is case-insensitive, so don't worry about capitalisation.
