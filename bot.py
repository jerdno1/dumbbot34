import discord
from discord.ext import commands
import aiohttp
import random
import os
import json

intents = discord.Intents.default()
intents.message_content = True

# ── Config ────────────────────────────────────────────────────────────────────
PREFIX = os.environ.get("BOT_PREFIX", ".")
BOORU_API_BASE = "https://api.rule34.xxx/index.php"
BOORU_USER_ID = os.environ.get("BOORU_USER_ID", "")
BOORU_API_KEY = os.environ.get("BOORU_API_KEY", "")
FAVOURITES_FILE = "favourites.json"

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ── Favourites storage ────────────────────────────────────────────────────────

def load_favourites() -> dict:
    if not os.path.exists(FAVOURITES_FILE):
        return {}
    with open(FAVOURITES_FILE, "r") as f:
        return json.load(f)

def save_favourites(data: dict):
    with open(FAVOURITES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_guild_favourites(guild_id: int) -> list:
    data = load_favourites()
    return data.get(str(guild_id), [])

def add_favourite(guild_id: int, post: dict) -> bool:
    """Returns False if already favourited, True if added."""
    data = load_favourites()
    key = str(guild_id)
    if key not in data:
        data[key] = []
    post_id = str(post.get("id", ""))
    if any(str(f.get("id", "")) == post_id for f in data[key]):
        return False
    data[key].append({
        "id": post.get("id"),
        "file_url": post.get("file_url") or post.get("sample_url", ""),
        "tags": post.get("tags", ""),
        "score": post.get("score", 0),
        "rating": post.get("rating", "?"),
        "created_at": post.get("created_at", ""),
    })
    save_favourites(data)
    return True

def remove_favourite(guild_id: int, post_id) -> bool:
    """Returns True if removed, False if not found."""
    data = load_favourites()
    key = str(guild_id)
    if key not in data:
        return False
    before = len(data[key])
    data[key] = [f for f in data[key] if str(f.get("id", "")) != str(post_id)]
    if len(data[key]) == before:
        return False
    save_favourites(data)
    return True

def apply_sort(posts: list, sort: str) -> list:
    if sort == "score_desc":
        return sorted(posts, key=lambda p: int(p.get("score", 0) or 0), reverse=True)
    elif sort == "score_asc":
        return sorted(posts, key=lambda p: int(p.get("score", 0) or 0))
    elif sort == "date_desc":
        return sorted(posts, key=lambda p: str(p.get("created_at", "")), reverse=True)
    elif sort == "date_asc":
        return sorted(posts, key=lambda p: str(p.get("created_at", "")))
    else:  # random (default)
        posts = list(posts)
        random.shuffle(posts)
        return posts

def parse_tags(args: tuple) -> str:
    """
    Join args into a tag string and append -ai.
    Supports exclusions via -tag syntax (passed through as-is).
    e.g. ("cat", "green_shirt", "-blue_shirt") -> "cat green_shirt -blue_shirt -ai"
    """
    tag_str = " ".join(args).strip()
    return (tag_str + " -ai").strip() if tag_str else "-ai"

# ── Booru fetcher ─────────────────────────────────────────────────────────────

async def fetch_booru_posts(tag_query: str) -> list | None:
    """Returns a list of posts, or None on API error."""
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
        async with session.get(BOORU_API_BASE, params=params) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
            if isinstance(data, dict) and not data.get("success", True):
                return None
            if not data:
                return []
            return [p for p in data if p.get("file_url") or p.get("sample_url")]

# ── Events ────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id}) | Prefix: {PREFIX}")

# ── Booru browser view ────────────────────────────────────────────────────────

class BooruView(discord.ui.View):
    def __init__(self, posts: list, guild_id: int, index: int = 0, is_favourites: bool = False):
        super().__init__(timeout=120)
        self.posts = posts
        self.guild_id = guild_id
        self.index = index
        self.is_favourites = is_favourites
        self._update_buttons()

    def _is_favourited(self) -> bool:
        post = self.posts[self.index]
        post_id = str(post.get("id", ""))
        favs = get_guild_favourites(self.guild_id)
        return any(str(f.get("id", "")) == post_id for f in favs)

    def _update_buttons(self):
        self.first_btn.disabled = self.index == 0
        self.prev_btn.disabled = self.index == 0
        self.next_btn.disabled = self.index >= len(self.posts) - 1
        self.last_btn.disabled = self.index >= len(self.posts) - 1

        if self._is_favourited():
            self.fav_btn.emoji = "💛"
            self.fav_btn.style = discord.ButtonStyle.success
        else:
            self.fav_btn.emoji = "⭐"
            self.fav_btn.style = discord.ButtonStyle.secondary

        self.unfav_btn.disabled = not self.is_favourites

    def build_embed(self) -> discord.Embed:
        post = self.posts[self.index]
        image_url = post.get("file_url") or post.get("sample_url", "")
        tag_str = post.get("tags", "").strip()
        score = post.get("score", "?")
        rating = post.get("rating", "?")
        total = len(self.posts)

        embed = discord.Embed(color=0x43B581)
        if image_url:
            embed.set_image(url=image_url)
        if tag_str:
            truncated = tag_str[:300] + ("..." if len(tag_str) > 300 else "")
            embed.description = f"-# {truncated}"
        footer_parts = [f"{self.index + 1} / {total}", f"Score: {score}", f"Rating: {rating}"]
        embed.set_footer(text="  |  ".join(footer_parts))
        return embed

    async def _refresh(self, interaction: discord.Interaction):
        self._update_buttons()
        try:
            await interaction.edit_original_response(embed=self.build_embed(), view=self)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def first_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.index = 0
        await self._refresh(interaction)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary, row=0)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.index -= 1
        await self._refresh(interaction)

    @discord.ui.button(emoji="⭐", style=discord.ButtonStyle.secondary, row=0)
    async def fav_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        post = self.posts[self.index]
        if self._is_favourited():
            remove_favourite(self.guild_id, post.get("id"))
            await interaction.followup.send("Removed from server favourites.", ephemeral=True)
        else:
            added = add_favourite(self.guild_id, post)
            if added:
                await interaction.followup.send("Added to server favourites! (ﾉ◕ヮ◕)ﾉ", ephemeral=True)
            else:
                await interaction.followup.send("Already in server favourites.", ephemeral=True)
        await self._refresh(interaction)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary, row=0)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.index += 1
        await self._refresh(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def last_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.index = len(self.posts) - 1
        await self._refresh(interaction)

    @discord.ui.button(label="Remove from Favourites", style=discord.ButtonStyle.danger, row=1)
    async def unfav_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        post = self.posts[self.index]
        removed = remove_favourite(self.guild_id, post.get("id"))
        if removed:
            self.posts.pop(self.index)
            if not self.posts:
                await interaction.edit_original_response(
                    content="No more favourites! (´• ω •`)", embed=None, view=None
                )
                self.stop()
                return
            self.index = min(self.index, len(self.posts) - 1)
            await interaction.followup.send("Removed from server favourites.", ephemeral=True)
        else:
            await interaction.followup.send("Couldn't find that post in favourites.", ephemeral=True)
        await self._refresh(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

# ── Shared booru command logic ─────────────────────────────────────────────────

async def booru_cmd(ctx: commands.Context, sort: str, args: tuple):
    tag_query = parse_tags(args)
    async with ctx.typing():
        try:
            posts = await fetch_booru_posts(tag_query)
        except Exception as e:
            await ctx.send(f"Something went wrong: {e}")
            return

    if posts is None:
        await ctx.send("Couldn't reach the booru API right now. (´• ω •`)")
        return
    if not posts:
        await ctx.send("No results found for those tags!")
        return

    posts = apply_sort(posts, sort)
    view = BooruView(posts, guild_id=ctx.guild.id)
    await ctx.send(embed=view.build_embed(), view=view)

# ── Booru commands ─────────────────────────────────────────────────────────────

@bot.command(name="random", aliases=["rand", "r"])
async def cmd_random(ctx: commands.Context, *args):
    """Random sort. Usage: .random [tags] [-excluded_tags]"""
    await booru_cmd(ctx, "random", args)

@bot.command(name="top", aliases=["best", "highest"])
async def cmd_top(ctx: commands.Context, *args):
    """High to low score. Usage: .top [tags] [-excluded_tags]"""
    await booru_cmd(ctx, "score_desc", args)

@bot.command(name="bottom", aliases=["worst", "lowest", "flop"])
async def cmd_bottom(ctx: commands.Context, *args):
    """Low to high score. Usage: .bottom [tags] [-excluded_tags]"""
    await booru_cmd(ctx, "score_asc", args)

@bot.command(name="date", aliases=["new", "newest", "recent"])
async def cmd_date(ctx: commands.Context, *args):
    """Most recent first. Usage: .date [tags] [-excluded_tags]"""
    await booru_cmd(ctx, "date_desc", args)

@bot.command(name="favs", aliases=["favourites", "favorites", "faves"])
async def cmd_favs(ctx: commands.Context):
    """Browse this server's favourited posts."""
    if not ctx.guild:
        await ctx.send("This command only works in a server!")
        return

    posts = get_guild_favourites(ctx.guild.id)
    if not posts:
        await ctx.send("This server has no favourited posts yet! Use ⭐ in the booru browser to add some.")
        return

    posts = apply_sort(posts, "random")
    view = BooruView(posts, guild_id=ctx.guild.id, is_favourites=True)
    await ctx.send(embed=view.build_embed(), view=view)

# ── .help ─────────────────────────────────────────────────────────────────────

@bot.command(name="help")
async def cmd_help(ctx: commands.Context):
    p = PREFIX
    embed = discord.Embed(title="Commands", color=0x2B2D31)
    embed.add_field(name=f"{p}random [tags]", value="Browse posts in random order", inline=False)
    embed.add_field(name=f"{p}top [tags]", value="Browse posts, highest score first", inline=False)
    embed.add_field(name=f"{p}bottom [tags]", value="Browse posts, lowest score first", inline=False)
    embed.add_field(name=f"{p}date [tags]", value="Browse posts, newest first", inline=False)
    embed.add_field(name=f"{p}favs", value="Browse this server's favourited posts", inline=False)
    embed.add_field(name=f"{p}meme", value="Random meme from Reddit", inline=False)
    embed.add_field(name=f"{p}ping", value="Check bot latency", inline=False)
    embed.set_footer(text=f"Tags example: {p}random cat green_shirt -blue_shirt")
    await ctx.send(embed=embed)

# ── .meme ─────────────────────────────────────────────────────────────────────

@bot.command(name="meme")
async def cmd_meme(ctx: commands.Context):
    """Random meme from Reddit."""
    subreddits = ["memes", "dankmemes", "me_irl", "shitposting", "196"]
    sub = random.choice(subreddits)
    url = f"https://www.reddit.com/r/{sub}/random/.json"

    async with ctx.typing():
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

# ── .ping ─────────────────────────────────────────────────────────────────────

@bot.command(name="ping")
async def cmd_ping(ctx: commands.Context):
    """Check bot latency."""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: **{latency}ms**")

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable not set!")
    bot.run(token)
