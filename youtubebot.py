import discord

client = discord.Client()
with open('token.txt') as t:
    token = t.read()

@client.event
async def on_ready():
    print(f"We have logged in as {client.user}!")

@client.event
async def on_message(message):
    if message.author == client.user:
        return # ignore messages from ourself

    if message.content.startswith('.p ') or message.content.startswith('.play '):
        if message.author.voice == None:
            await message.channel.send("Must be in a voice channel to use this command.")
            return
        await message.author.voice.channel.connect()

client.run(token)