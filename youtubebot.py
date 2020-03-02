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

    if message.content.startswith('.'):
        await message.channel.send('whas gewd niggaaaaaa')

client.run(token)