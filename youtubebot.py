import discord

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from pytube import YouTube

import os
import asyncio

PATH = './sample/'

queue = []
voice = None

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
        await play(message)

    if message.content.startswith('.skip'):
        await skip(message)

    if message.content.startswith('.clear'):
        await clear(message)

    if message.content.startswith('.np'):
        await np(message)

async def np(message):
    pass

# todo: test direct url linking

async def play(message):
    global voice

    if message.author.voice == None:
        await message.channel.send('Must be in a voice channel to use this command.')
        return
    if voice != None and voice.channel != message.author.voice.channel:
        await message.channel.send('Must be in the same voice channel as the bot to use this command.')
        return
    query = message.content[message.content.index(' ')+1:]
    video_data = None
    if query.startswith('https://www.youtube.com/watch?v=') or query.startswith('https://youtube.com/watch?v='):
        await message.channel.send(f'Getting video...')
        vid_id = query[query.index('=')+1:]
        video_data = (get_title(vid_id), vid_id)
    elif query.startswith('https://youtu.be/'):
        await message.channel.send(f'Getting video...')
        vid_id = query[query.index('be/')+3:]
        video_data = (get_title(vid_id), vid_id)
    elif query.startswith('https://www.youtube.com/embed/') or query.startswith('https://youtube.com/embed/'):
        await message.channel.send(f'Getting video...')
        vid_id = query[query.index('embed/')+6:]
        video_data = (get_title(vid_id), vid_id)
    else:
        await message.channel.send(f'Searching for: `{query}`')
        video_data = search(query)
        if video_data == None:
            await message.channel.send('No results found.')
            return
    fname, bitrate = get_audio(video_data[1], message.channel)
    audio = discord.FFmpegOpusAudio(f'{PATH}{fname}', bitrate=bitrate)
    queue.append((audio, fname))
    if len(queue) > 1: # 1, not 0, because we just added to it
        await message.channel.send(f'Adding to queue `{video_data[0]}` https://www.youtube.com/watch?v={video_data[1]}')
    else:
        await message.channel.send(f'Now playing `{video_data[0]}` https://www.youtube.com/watch?v={video_data[1]}')
        voice = await message.author.voice.channel.connect()
        voice.play(queue[0][0], after=after)
    return

async def skip(message):
    voice.stop()
    await message.channel.send('Skipped.')

async def clear(message):
    voice.stop()
    queue.clear()
    await message.channel.send('Cleared.')

def search(query):
    youtube = build('youtube', 'v3', developerKey=ytapi)
    search_response = youtube.search().list(q=query, part='id,snippet', maxResults=25).execute()
    for result in search_response.get('items', []):
        if result['id']['kind'] == 'youtube#video':
            return (result['snippet']['title'], result['id']['videoId'])
    return None

def get_title(vid_id):
    return YouTube(f'https://youtu.be/{vid_id}').title

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
    global voice

    if err != None:
        print(err)

    if len(queue) > 0:
        os.remove(PATH+queue[0][1])
        queue.pop(0)
    if len(queue) > 0: # this looks redundant but it isn't because len() changes after popping
        voice.play(queue[0][0], after=after)
    else:
        coro = voice.disconnect()
        fut = asyncio.run_coroutine_threadsafe(coro, client.loop)
        try:
            fut.result()
        except:
            pass
        voice = None
    # todo: remove file

client.run(token)