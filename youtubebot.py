import discord

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from pytube import YouTube

import os.path

PATH = './sample/'

client = discord.Client()
with open('token.txt') as t:
    lines = t.readlines()
    token = lines[0][:-1] # remove trailing newline
    ytapi = lines[1][:-1]

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

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
        video_data = search(query)
        if video_data == None:
            await message.channel.send('No results found.')
            return
        await message.channel.send(f'Now playing `{video_data[0]}`: https://www.youtube.com/watch?v={video_data[1]}')
        voice = await message.author.voice.channel.connect()
        fname, bitrate = get_audio(video_data[1], message.channel)
        audio = discord.FFmpegOpusAudio(f'{PATH}{fname}', bitrate=bitrate)
        voice.play(audio, after=after)
        return

def search(query):
    youtube = build('youtube', 'v3', developerKey=ytapi)
    search_response = youtube.search().list(q=query, part='id,snippet', maxResults=25).execute()
    for result in search_response.get('items', []):
        if result['id']['kind'] == 'youtube#video':
            return (result['snippet']['title'], result['id']['videoId'])
    return None

def get_audio(vid_id, channel):
    yt = YouTube(f'https://youtu.be/{vid_id}')
    if yt.length > 3600:
        channel.send("Video is longer than 1 hour, may take a moment to begin...")
    lowest_bitrate = yt.streams.filter(only_audio=True).order_by('abr')[0] # lowest quality audio because we want that SPEED
    filename = vid_id
    index = 0
    while os.path.isfile(f'{PATH}{filename}'):
        filename = f'{vid_id}#{index}'
        index += 1
    lowest_bitrate.download(output_path=PATH, filename=filename)
    return (f'{filename}.{lowest_bitrate.mime_type[lowest_bitrate.mime_type.index("/")+1:]}', int(lowest_bitrate.abr[:-4]))

def after(err):
    if err != None:
        print(err)

    # todo: cleanup, leave, remove file

client.run(token)