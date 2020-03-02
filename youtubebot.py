import discord

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


client = discord.Client()
with open('token.txt') as t:
    lines = t.readlines()
    token = lines[0][:-1] # remove trailing newline
    ytapi = lines[1][:-1]

@client.event
async def on_ready():
    print(f"We have logged in as {client.user}!")

@client.event
async def on_message(message):
    if message.author == client.user:
        return # ignore messages from ourself

    if message.content.startswith('.p ') or message.content.startswith('.play '):
        if message.author.voice == None:
            await message.channel.send('Must be in a voice channel to use this command.')
            return
        query = message.content[message.content.index(' ')+1:]
        await message.channel.send(f'Searching for: `{query}`')
        video = search(query)
        if video == None:
            await message.channel.send('No results found.')
            return
        await message.channel.send(f'Now playing `{video[0]}`: https://www.youtube.com/watch?v={video[1]}')
        await message.author.voice.channel.connect()

def search(query):
    youtube = build('youtube', 'v3', developerKey=ytapi)
    search_response = youtube.search().list(q=query, part='id,snippet', maxResults=25).execute()
    for result in search_response.get('items', []):
        if result['id']['kind'] == 'youtube#video':
            return (result['snippet']['title'], result['id']['videoId'])
    return None

client.run(token)