import discord
from discord.ext import commands

import traceback

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from pytube import YouTube

import glob
import os
import sys
import subprocess as sp
import asyncio
from functools import partial

PATH = 'sample/'

welcome_message = '''Thanks for adding YoutubeBot! My command prefix is `.` So far, there are three commands:
`.play [youtube url or search query]`  - plays a song from the url or from the search query
`.skip` - skips the current song and leaves the channel if the queue is empty
`.clear` - clears the queue and leaves the voice channel'''

servers = {} # "server id": (voice, [queue])
try:
    with open('servers.txt') as s:
        for line in s.readlines():
            servers[int(line[:-1])] = [None, []] # remove trailing newline
except FileNotFoundError:
    pass

bot = commands.Bot(command_prefix='.')

# client = discord.Client()
with open('token.txt') as t:
    lines = t.readlines()
    token = lines[0][:-1]
    ytapi = lines[1][:-1]

@bot.event
async def on_command_error(ctx, err):
    print(f"Something broke, restarting: {ctx.channel.id}")
    traceback.print_exception(type(err), err, err.__traceback__)
    print(err)
    print(sys.exc_info())
    await ctx.send("Something broke, restarting. Give me a few seconds.")
    sp.run(['./restart.sh'])

@bot.event
async def on_guild_join(guild):
    servers[guild.id] = [None, []]
    with open('servers.txt', 'a') as s:
        s.write(f'{guild.id}\n')
    for text_channel in guild.text_channels:
        try:
            await text_channel.send(welcome_message)
            return
        except discord.errors.Forbidden:
            print("Couldn't send welcome message to a voice channel.")

@bot.event
async def on_guild_remove(guild):
    servers.pop(guild.id)
    with open("servers.txt", "r+") as f:
        d = f.readlines()
        f.seek(0)
        for i in d:
            if i != f'{guild.id}\n':
                f.write(i)
        f.truncate()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# @bot.event
# async def on_voice_state_update(member, before, after):
#     if member == bot.user:
#         if before.channel is not None and before.channel != after.channel: # we only care about channel-related changes
#             if after.channel is None and servers[before.channel.guild.id][0] is not None: # manually disconnected from voice channel
#                 info = servers[before.channel.guild.id]
#                 info[0] = None
#                 while len(info[1]) > 0:
#                     os.remove(info[1][0][1])
#                     info[1].pop(0)
#             else: # moved to another voice channel
#                 servers[before.channel.guild.id][0] = get_relevant_voice_client(after.channel.id)


@bot.command(name='np')
async def np(ctx):
    pass # todo

@bot.command(name='p')
async def p(ctx, *, query):
    await play(ctx, query=query)

@bot.command(name='play')
async def play(ctx, *, query):
    info = servers[ctx.guild.id]

    if ctx.author.voice == None:
        await ctx.send('Must be in a voice channel to use this command.')
        return
    if info[0] != None and info[0].channel != ctx.author.voice.channel:
        await ctx.send('Must be in the same voice channel as the bot to use this command.')
        return
    video_data = None
    if query.startswith('https://www.youtube.com/watch?v=') or query.startswith('https://youtube.com/watch?v='):
        await ctx.send(f'Getting video...')
        vid_id = query[query.index('=')+1:]
        video_data = (get_title(vid_id), vid_id)
    elif query.startswith('https://youtu.be/'):
        await ctx.send(f'Getting video...')
        vid_id = query[query.index('be/')+3:]
        video_data = (get_title(vid_id), vid_id)
    elif query.startswith('https://www.youtube.com/embed/') or query.startswith('https://youtube.com/embed/'):
        await ctx.send(f'Getting video...')
        vid_id = query[query.index('embed/')+6:]
        video_data = (get_title(vid_id), vid_id)
    else:
        await ctx.send(f'Searching for: `{query}`')
        video_data = search(query)
        if video_data == None:
            await ctx.send('No results found.')
            return
    print(video_data)
    path, bitrate = get_audio(video_data[1], ctx.channel)
    audio = discord.FFmpegOpusAudio(path, bitrate=bitrate)
    info[1].append((audio, path))
    print(f'queue: {info[1]}')
    if len(info[1]) > 1: # 1, not 0, because we just added to it
        await ctx.send(f'Adding to queue `{video_data[0]}` https://www.youtube.com/watch?v={video_data[1]}')
    else:
        await ctx.send(f'Now playing `{video_data[0]}` https://www.youtube.com/watch?v={video_data[1]}')
        info[0] = await ctx.author.voice.channel.connect()
        info[0].play(info[1][0][0], after=partial(after, None, ctx.guild.id))
    return

@bot.command()
async def s(ctx):
    await skip(ctx)

@bot.command()
async def skip(ctx):
    info = servers[ctx.guild.id]

    if ctx.author.voice == None:
        await ctx.send('Must be in a voice channel to use this command.')
        return
    if info[0] != None and info[0].channel != ctx.author.voice.channel:
        await ctx.send('Must be in the same voice channel as the bot to use this command.')
        return
    if info[0] == None:
        await ctx.send('Nothing playing.')
        return
    info[0].stop()
    await ctx.send('Skipped.')

@bot.command()
async def clear(ctx):
    info = servers[ctx.guild.id]

    if ctx.author.voice == None:
        await ctx.send('Must be in a voice channel to use this command.')
        return
    if info[0] != None and info[0].channel != ctx.author.voice.channel:
        await ctx.send('Must be in the same voice channel as the bot to use this command.')
        return
    info[0].stop()
    while len(info[1]) > 0:
        os.remove(info[1][0][1])
        info[1].pop(0)
    await ctx.send('Cleared.')

# def get_relevant_voice_client(channel_id):
#     for v in bot.voice_clients:
#         if channel_id == v.channel.id:
#             return v
#     return None

def get_voice(server):
    return servers[server][0]

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
    print(f'https://youtu.be/{vid_id}')
    yt = YouTube(f'https://youtu.be/{vid_id}')
    print(yt)
    if yt.length > 3600:
        channel.send("Video is longer than 1 hour, may take a moment to begin...")
    lowest_bitrate = yt.streams.filter(only_audio=True).order_by('abr')[0] # lowest quality audio because we want that SPEED
    print(lowest_bitrate)
    filename = f'{vid_id}_0'
    index = 0
    while glob.glob(f'{PATH}{filename}.*'):
        filename = f'{vid_id}_{index}'
        index += 1
    path = lowest_bitrate.download(output_path=PATH, filename=filename, skip_existing=False)
    print(f'{path=}')
    return (path, int(lowest_bitrate.abr[:-4]))

def after(err, *args):
    info = servers[args[0]]

    if err != None:
        print(err)

    if len(info[1]) > 0:
        os.remove(info[1][0][1])
        info[1].pop(0)
    if len(info[1]) > 0: # this looks redundant but it isn't because len() changes after popping
        info[0].play(info[1][0][0], after=partial(after, None, args[0]))
    else:
        coro = info[0].disconnect()
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except:
            pass
        info[0] = None

bot.run(token)