import discord
from discord.ext import commands
from flask import Flask, request, redirect
import requests
import os
import asyncio

# Load environment variables (set in Railway)
TOKEN = os.getenv("TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")  # Set this to your Railway domain
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

# Set up Discord bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask web server
app = Flask(__name__)

@app.route("/")
def home():
    return '<a href="/login">Login with Discord</a>'

@app.route("/login")
def login():
    discord_auth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds"
    return redirect(discord_auth_url)

@app.route("/callback")
async def callback():
    code = request.args.get("code")
    if not code:
        return "Error: No code provided", 400  # If no code, return error

    # Exchange code for access token
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify guilds"
    }

    # Sending a POST request to get the access token
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    
    if response.status_code != 200:
        return f"Error getting access token: {response.text}", 500  # If the token exchange fails

    token_info = response.json()

    if "access_token" not in token_info:
        return "Error: No access token received", 500  # If the token is not in the response

    access_token = token_info["access_token"]

    # Fetch user info with the access token
    user_headers = {"Authorization": f"Bearer {access_token}"}
    user_info = requests.get("https://discord.com/api/users/@me", headers=user_headers).json()

    if "username" not in user_info:
        return "Error: Could not retrieve user info", 500  # If user info can't be fetched

    # Fetch user guilds (servers)
    guilds_info = requests.get("https://discord.com/api/users/@me/guilds", headers=user_headers).json()

    # Format user data
    username = f"{user_info['username']}#{user_info['discriminator']}"
    user_servers = "\n".join([f"- {g['name']} (ID: {g['id']})" for g in guilds_info])

    # Send user data to the Discord log channel
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(f"**New Authenticated User**\n👤 User: `{username}`\n🖥️ Servers:\n{user_servers}")

    return f"Success! Your info has been logged.\nUser: `{username}`\nServers:\n{user_servers}"

@bot.event
async def on_ready():
    print(f"✅ Bot is online! Logged in as {bot.user}")

# Run Flask and Discord bot together
async def start():
    loop = asyncio.get_event_loop()
    loop.create_task(app.run(host="0.0.0.0", port=5000))
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(start())
