import discord
from discord import app_commands
import aiohttp
import random
import os
import json

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ── Config ────────────────────────────────────────────────────────────────────
BOORU_API_BASE = "https://api.24booru.xyz/index.php"
BOORU_USER_ID = os.environ.get("BOORU_USER_ID", "")
BOORU_API_KEY = os.environ.get("BOORU_API_KEY", "")
FAVOURITES_FILE = "favourites.json"

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

# ── Events ────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

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

# ── /help ─────────────────────────────────────────────────────────────────────

@tree.command(name="help", description="List all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="Commands", color=0x2B2D31)
    embed.add_field(name="/meme", value="Random meme from Reddit", inline=False)
    embed.add_field(name="/booru [tags] [sort]", value="Browse 24booru posts, optional tags and sort order", inline=False)
    embed.add_field(name="/favorites [sort]", value="Browse this server's favourited booru posts", inline=False)
    embed.add_field(name="/ping", value="Check bot latency", inline=False)
    await interaction.response.send_message(embed=embed)

# ── /meme ─────────────────────────────────────────────────────────────────────

@tree.command(name="meme", description="Random meme from Reddit")
async def meme(interaction: discord.Interaction):
    await interaction.response.defer()
    subreddits = ["memes", "dankmemes", "me_irl", "shitposting", "196"]
    sub = random.choice(subreddits)
    url = f"https://www.reddit.com/r/{sub}/random/.json"

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

# ── /booru ────────────────────────────────────────────────────────────────────

@tree.command(name="booru", description="Browse 24booru posts")
@app_commands.describe(
    tags="Optional tags to filter posts",
    sort="Sort order (default: random)"
)
@app_commands.choices(sort=[
    app_commands.Choice(name="Random (default)", value="random"),
    app_commands.Choice(name="Score: High to Low", value="score_desc"),
    app_commands.Choice(name="Score: Low to High", value="score_asc"),
    app_commands.Choice(name="Date: Newest First", value="date_desc"),
    app_commands.Choice(name="Date: Oldest First", value="date_asc"),
])
async def booru(
    interaction: discord.Interaction,
    tags: str = "",
    sort: str = "random"
):
    await interaction.response.defer()

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
                    await interaction.followup.send("Couldn't reach the 24booru API right now. (´• ω •`)")
                    return
                data = await resp.json(content_type=None)

                if isinstance(data, dict) and not data.get("success", True):
                    await interaction.followup.send("The booru search is down right now, try again later!")
                    return
                if not data:
                    await interaction.followup.send("No results found for those tags!")
                    return

                posts = [p for p in data if p.get("file_url") or p.get("sample_url")]
                if not posts:
                    await interaction.followup.send("Got results but none had images, try again!")
                    return

                posts = apply_sort(posts, sort)
                view = BooruView(posts, guild_id=interaction.guild_id)
                await interaction.followup.send(embed=view.build_embed(), view=view)

        except Exception as e:
            await interaction.followup.send(f"Something went wrong: {e}")

# ── /favorites ────────────────────────────────────────────────────────────────

@tree.command(name="favorites", description="Browse this server's favourited booru posts")
@app_commands.describe(sort="Sort order (default: random)")
@app_commands.choices(sort=[
    app_commands.Choice(name="Random (default)", value="random"),
    app_commands.Choice(name="Score: High to Low", value="score_desc"),
    app_commands.Choice(name="Score: Low to High", value="score_asc"),
    app_commands.Choice(name="Date: Newest First", value="date_desc"),
    app_commands.Choice(name="Date: Oldest First", value="date_asc"),
])
async def favorites(interaction: discord.Interaction, sort: str = "random"):
    if not interaction.guild:
        await interaction.response.send_message("This command only works in a server!", ephemeral=True)
        return

    posts = get_guild_favourites(interaction.guild_id)
    if not posts:
        await interaction.response.send_message(
            "This server has no favourited posts yet! Use ⭐ in the booru browser to add some."
        )
        return

    posts = apply_sort(posts, sort)
    view = BooruView(posts, guild_id=interaction.guild_id, is_favourites=True)
    await interaction.response.send_message(embed=view.build_embed(), view=view)

# ── /ping ─────────────────────────────────────────────────────────────────────

@tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: **{latency}ms**")

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable not set!")
    bot.run(token)
