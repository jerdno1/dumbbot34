import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ── Trivia questions ──────────────────────────────────────────────────────────
TRIVIA = [
    {"q": "What is the capital of Slovakia?", "a": "bratislava"},
    {"q": "How many sides does a hexagon have?", "a": "6"},
    {"q": "What element has the symbol Fe?", "a": "iron"},
    {"q": "Who invented the telephone?", "a": "alexander graham bell"},
    {"q": "What is 12 × 12?", "a": "144"},
    {"q": "Which planet is closest to the Sun?", "a": "mercury"},
    {"q": "What gas do plants absorb from the air?", "a": "carbon dioxide"},
    {"q": "How many continents are there?", "a": "7"},
    {"q": "What is the fastest land animal?", "a": "cheetah"},
    {"q": "Who painted the Mona Lisa?", "a": "leonardo da vinci"},
    {"q": "What year did World War II end?", "a": "1945"},
    {"q": "What is the chemical symbol for gold?", "a": "au"},
    {"q": "How many strings does a standard guitar have?", "a": "6"},
    {"q": "What is the square root of 64?", "a": "8"},
    {"q": "Which country has the largest population?", "a": "india"},
]

# Active trivia sessions per channel (channel_id -> question dict)
active_trivia: dict[int, dict] = {}

# 8-ball responses
EIGHTBALL = [
    "It is certain.", "It is decidedly so.", "Without a doubt.",
    "Yes, definitely.", "You may rely on it.", "As I see it, yes.",
    "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
    "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful.",
]

FORTUNES = [
    "A surprise is waiting for you around the corner.",
    "Hard work pays off -- eventually.",
    "Someone is thinking about you right now.",
    "Your next big idea will come from the most unexpected place.",
    "The stars say: touch grass.",
    "You will find something you lost long ago.",
    "Be patient. Good things take time.",
    "A new friendship will change your life.",
    "Do not be afraid to take the first step.",
    "The cookie says nothing. The cookie is wise.",
]

# ── Events ────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Slash commands synced!")

# ── /meme ─────────────────────────────────────────────────────────────────────

@bot.tree.command(name="meme", description="Get a random meme from Reddit")
async def meme(interaction: discord.Interaction):
    subreddits = ["memes", "dankmemes", "me_irl", "shitposting", "196"]
    sub = random.choice(subreddits)
    url = f"https://www.reddit.com/r/{sub}/random/.json"

    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        headers = {"User-Agent": "discord-bot/1.0"}
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    await interaction.followup.send("Couldn't fetch a meme right now, try again! (´• ω •`)")
                    return
                data = await resp.json()
                post = data[0]["data"]["children"][0]["data"]
                title = post["title"]
                image = post.get("url_overridden_by_dest", "")
                post_url = f"https://reddit.com{post['permalink']}"

                if not image.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                    await interaction.followup.send("Couldn't find an image meme, try again!")
                    return

                embed = discord.Embed(title=title, url=post_url, color=0xFF4500)
                embed.set_image(url=image)
                embed.set_footer(text=f"r/{sub}")
                await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"Something went wrong: {e}")

# ── /8ball ────────────────────────────────────────────────────────────────────

@bot.tree.command(name="8ball", description="Ask the magic 8-ball a question")
@app_commands.describe(question="Your yes/no question")
async def eightball(interaction: discord.Interaction, question: str):
    answer = random.choice(EIGHTBALL)
    embed = discord.Embed(color=0x2B2D31)
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="🎱 Answer", value=answer, inline=False)
    await interaction.response.send_message(embed=embed)

# ── /fortune ──────────────────────────────────────────────────────────────────

@bot.tree.command(name="fortune", description="Get your fortune for today")
async def fortune(interaction: discord.Interaction):
    msg = random.choice(FORTUNES)
    embed = discord.Embed(title="🔮 Your Fortune", description=msg, color=0x9B59B6)
    embed.set_footer(text="Accuracy not guaranteed (ﾉ◕ヮ◕)ﾉ")
    await interaction.response.send_message(embed=embed)

# ── /trivia ───────────────────────────────────────────────────────────────────

@bot.tree.command(name="trivia", description="Start a trivia question! You have 30 seconds to answer.")
async def trivia(interaction: discord.Interaction):
    channel_id = interaction.channel_id

    if channel_id in active_trivia:
        await interaction.response.send_message("A trivia question is already active in this channel!", ephemeral=True)
        return

    question = random.choice(TRIVIA)
    active_trivia[channel_id] = question

    embed = discord.Embed(
        title="🧠 Trivia Time!",
        description=question["q"],
        color=0xF1C40F
    )
    embed.set_footer(text="Type your answer in chat! You have 30 seconds.")
    await interaction.response.send_message(embed=embed)

    def check(msg: discord.Message):
        return (
            msg.channel.id == channel_id
            and not msg.author.bot
            and msg.content.strip().lower() == question["a"].lower()
        )

    try:
        msg = await bot.wait_for("message", check=check, timeout=30.0)
        del active_trivia[channel_id]
        await msg.channel.send(f"✅ Correct, {msg.author.mention}! The answer was **{question['a']}**.")
    except asyncio.TimeoutError:
        if channel_id in active_trivia:
            del active_trivia[channel_id]
        await interaction.channel.send(f"⏰ Time's up! The answer was **{question['a']}**.")

# ── /randommeme ───────────────────────────────────────────────────────────────
BOORU_API_BASE = "https://api.rule34.xxx/index.php"
BOORU_USER_ID = os.environ.get("BOORU_USER_ID", "")
BOORU_API_KEY = os.environ.get("BOORU_API_KEY", "")

@bot.tree.command(name="randommeme", description="Get a random meme from 24booru")
@app_commands.describe(tags="Optional tags to search (space separated)")
async def randommeme(interaction: discord.Interaction, tags: str = ""):
    await interaction.response.defer()

    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "json": "1",
        "limit": "100",
        "pid": random.randint(0, 10),
        "tags": tags.strip() if tags else "",
    }
    if BOORU_USER_ID and BOORU_API_KEY:
        params["user_id"] = BOORU_USER_ID
        params["api_key"] = BOORU_API_KEY

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(BOORU_API_BASE, params=params) as resp:
                if resp.status != 200:
                    await interaction.followup.send("Couldn't reach the 24booru API right now. (´• ω •`)")
                    return
                data = await resp.json(content_type=None)

                if isinstance(data, dict) and not data.get("success", True):
                    await interaction.followup.send("The booru search is down right now, try again later!")
                    return

                if not data:
                    await interaction.followup.send("No results found for those tags!")
                    return

                post = random.choice(data)
                image_url = post.get("file_url") or post.get("sample_url")
                source = post.get("source", "")
                tag_str = post.get("tags", "")[:200]

                if not image_url:
                    await interaction.followup.send("Got a result but couldn't find an image URL, try again!")
                    return

                embed = discord.Embed(color=0x43B581)
                embed.set_image(url=image_url)
                if source:
                    embed.add_field(name="Source", value=source[:200], inline=False)
                if tag_str:
                    embed.set_footer(text=f"Tags: {tag_str}")
                await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Something went wrong: {e}")

# ── /coinflip ─────────────────────────────────────────────────────────────────

@bot.tree.command(name="coinflip", description="Flip a coin")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    emoji = "🪙"
    await interaction.response.send_message(f"{emoji} **{result}!**")

# ── /roll ─────────────────────────────────────────────────────────────────────

@bot.tree.command(name="roll", description="Roll a dice (default d6, supports d4/d6/d8/d10/d12/d20/d100)")
@app_commands.describe(sides="Number of sides: 4, 6, 8, 10, 12, 20, or 100")
async def roll(interaction: discord.Interaction, sides: int = 6):
    valid = [4, 6, 8, 10, 12, 20, 100]
    if sides not in valid:
        await interaction.response.send_message(f"Pick a valid dice: {', '.join(f'd{v}' for v in valid)}", ephemeral=True)
        return
    result = random.randint(1, sides)
    await interaction.response.send_message(f"🎲 You rolled a **d{sides}** and got **{result}**!")

# ── /ping ─────────────────────────────────────────────────────────────────────

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: **{latency}ms**")

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable not set!")
    bot.run(token)
