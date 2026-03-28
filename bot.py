import discord
from discord.ext import commands
import aiohttp
import random
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".m ", intents=intents, help_command=None)

# ── Config ────────────────────────────────────────────────────────────────────
BOORU_API_BASE = "https://api.24booru.xyz/index.php"
BOORU_USER_ID = os.environ.get("BOORU_USER_ID", "")
BOORU_API_KEY = os.environ.get("BOORU_API_KEY", "")

# ── Trivia ────────────────────────────────────────────────────────────────────
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

active_trivia: dict[int, dict] = {}

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
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

# ── .m help ───────────────────────────────────────────────────────────────────

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(title="Commands", color=0x2B2D31)
    embed.add_field(name=".m meme", value="Random meme from Reddit", inline=False)
    embed.add_field(name=".m randommeme [tags]", value="Random post from 24booru, optional tags", inline=False)
    embed.add_field(name=".m 8ball <question>", value="Ask the magic 8-ball", inline=False)
    embed.add_field(name=".m fortune", value="Get your fortune", inline=False)
    embed.add_field(name=".m trivia", value="Start a trivia question", inline=False)
    embed.add_field(name=".m coinflip", value="Flip a coin", inline=False)
    embed.add_field(name=".m roll [sides]", value="Roll a dice (d4/d6/d8/d10/d12/d20/d100)", inline=False)
    embed.add_field(name=".m ping", value="Check bot latency", inline=False)
    await ctx.send(embed=embed)

# ── .m meme ───────────────────────────────────────────────────────────────────

@bot.command(name="meme")
async def meme(ctx):
    subreddits = ["memes", "dankmemes", "me_irl", "shitposting", "196"]
    sub = random.choice(subreddits)
    url = f"https://www.reddit.com/r/{sub}/random/.json"

    async with aiohttp.ClientSession() as session:
        headers = {"User-Agent": "discord-bot/1.0"}
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    await ctx.send("Couldn't fetch a meme right now, try again! (´• ω •`)")
                    return
                data = await resp.json()
                post = data[0]["data"]["children"][0]["data"]
                title = post["title"]
                image = post.get("url_overridden_by_dest", "")
                post_url = f"https://reddit.com{post['permalink']}"

                if not image.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                    await ctx.send("Couldn't find an image meme, try again!")
                    return

                embed = discord.Embed(title=title, url=post_url, color=0xFF4500)
                embed.set_image(url=image)
                embed.set_footer(text=f"r/{sub}")
                await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Something went wrong: {e}")

# ── Booru browser view ────────────────────────────────────────────────────────

class BooruView(discord.ui.View):
    def __init__(self, posts: list, index: int = 0):
        super().__init__(timeout=120)
        self.posts = posts
        self.index = index
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.index == 0
        self.next_btn.disabled = self.index >= len(self.posts) - 1

    def build_embed(self) -> discord.Embed:
        post = self.posts[self.index]
        image_url = post.get("file_url") or post.get("sample_url", "")
        tag_str = post.get("tags", "").strip()
        total = len(self.posts)

        embed = discord.Embed(color=0x43B581)
        if image_url:
            embed.set_image(url=image_url)
        if tag_str:
            truncated = tag_str[:300] + ("..." if len(tag_str) > 300 else "")
            embed.description = f"-# {truncated}"
        embed.set_footer(text=f"{self.index + 1} / {total}")
        return embed

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.index -= 1
        self._update_buttons()
        try:
            await interaction.edit_original_response(embed=self.build_embed(), view=self)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.index += 1
        self._update_buttons()
        try:
            await interaction.edit_original_response(embed=self.build_embed(), view=self)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

# ── .m randommeme [tags] ──────────────────────────────────────────────────────

@bot.command(name="randommeme")
async def randommeme(ctx, *, tags: str = ""):
    # Always append -ai to filter out AI-generated content
    tag_query = (tags.strip() + " -ai").strip() if tags.strip() else "-ai"

    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "json": "1",
        "limit": "100",
        "pid": random.randint(0, 10),
        "tags": tag_query,
    }
    if BOORU_USER_ID and BOORU_API_KEY:
        params["user_id"] = BOORU_USER_ID
        params["api_key"] = BOORU_API_KEY

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(BOORU_API_BASE, params=params) as resp:
                if resp.status != 200:
                    await ctx.send("Couldn't reach the 24booru API right now. (´• ω •`)")
                    return
                data = await resp.json(content_type=None)

                if isinstance(data, dict) and not data.get("success", True):
                    await ctx.send("The booru search is down right now, try again later!")
                    return
                if not data:
                    await ctx.send("No results found for those tags!")
                    return

                posts = [p for p in data if p.get("file_url") or p.get("sample_url")]
                if not posts:
                    await ctx.send("Got results but none had images, try again!")
                    return

                view = BooruView(posts, index=0)
                await ctx.send(embed=view.build_embed(), view=view)

        except Exception as e:
            await ctx.send(f"Something went wrong: {e}")

# ── .m 8ball <question> ───────────────────────────────────────────────────────

@bot.command(name="8ball")
async def eightball(ctx, *, question: str = ""):
    if not question:
        await ctx.send("Ask a question! e.g. `.m 8ball will I pass my exam`")
        return
    answer = random.choice(EIGHTBALL)
    embed = discord.Embed(color=0x2B2D31)
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="🎱 Answer", value=answer, inline=False)
    await ctx.send(embed=embed)

# ── .m fortune ────────────────────────────────────────────────────────────────

@bot.command(name="fortune")
async def fortune(ctx):
    msg = random.choice(FORTUNES)
    embed = discord.Embed(title="🔮 Your Fortune", description=msg, color=0x9B59B6)
    embed.set_footer(text="Accuracy not guaranteed (ﾉ◕ヮ◕)ﾉ")
    await ctx.send(embed=embed)

# ── .m trivia ─────────────────────────────────────────────────────────────────

@bot.command(name="trivia")
async def trivia(ctx):
    channel_id = ctx.channel.id

    if channel_id in active_trivia:
        await ctx.send("A trivia question is already active in this channel!")
        return

    question = random.choice(TRIVIA)
    active_trivia[channel_id] = question

    embed = discord.Embed(title="🧠 Trivia Time!", description=question["q"], color=0xF1C40F)
    embed.set_footer(text="Type your answer in chat! You have 30 seconds.")
    await ctx.send(embed=embed)

    def check(msg: discord.Message):
        return (
            msg.channel.id == channel_id
            and not msg.author.bot
            and msg.content.strip().lower() == question["a"].lower()
        )

    try:
        msg = await bot.wait_for("message", check=check, timeout=30.0)
        del active_trivia[channel_id]
        await ctx.send(f"✅ Correct, {msg.author.mention}! The answer was **{question['a']}**.")
    except asyncio.TimeoutError:
        if channel_id in active_trivia:
            del active_trivia[channel_id]
        await ctx.send(f"⏰ Time's up! The answer was **{question['a']}**.")

# ── .m coinflip ───────────────────────────────────────────────────────────────

@bot.command(name="coinflip")
async def coinflip(ctx):
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 **{result}!**")

# ── .m roll [sides] ───────────────────────────────────────────────────────────

@bot.command(name="roll")
async def roll(ctx, sides: int = 6):
    valid = [4, 6, 8, 10, 12, 20, 100]
    if sides not in valid:
        await ctx.send(f"Pick a valid dice: {', '.join(f'd{v}' for v in valid)}")
        return
    result = random.randint(1, sides)
    await ctx.send(f"🎲 You rolled a **d{sides}** and got **{result}**!")

# ── .m ping ───────────────────────────────────────────────────────────────────

@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: **{latency}ms**")

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable not set!")
    bot.run(token)
