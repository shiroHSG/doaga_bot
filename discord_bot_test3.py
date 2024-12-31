import asyncio
import discord
import yt_dlp as youtube_dl
from discord.ext import commands

import bs4
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from discord import FFmpegPCMAudio

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

TOKEN = 'MTIyOTY0Mzg1MzUyNzUxOTI2Mw.GOTqfv.RKzgkAy0QD-l5U1-a8Xy_YYaacuHs6QDG70tDE'

intents = discord.Intents.default()
intents.message_content = True

#봇 생성
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description='Relatively simple music bot example',
    intents=intents,
)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch1',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}
 
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# ytdl 객체 선언
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
 
# youtube 음악과 로컬 음악의 재생을 구별하기 위한 클래스 작성.
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.3):
        super().__init__(source, volume)
 
        self.data = data
 
        self.title = data.get('title')
        self.url = data.get('url')
 
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
 
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
 
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
 
 
# 음악 재생 클래스. 커맨드 포함.
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
 
    @commands.command()
    async def join(self, ctx):
        """Joins a voice channel"""
        
        channel = ctx.author.voice.channel
 
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
 
        await channel.connect()
 
   
    @commands.command(name="p")
    async def play(self, ctx, *, query):
        """Streams from a url or a search query"""

        # URL인지 검색어인지 확인
        if query.startswith("http://") or query.startswith("https://"):
            url = query
        else:
            # 검색어인 경우
            global entireText
            chromedriver_dir = "C:/Users/seong/OneDrive/바탕 화면/디스코드/chromedriver-win64/chromedriver.exe"
            service = Service(executable_path=chromedriver_dir)
            driver = webdriver.Chrome(service=service)
            driver.get("https://www.youtube.com/results?search_query="+query+"+lyrics")
            source = driver.page_source
            bs = bs4.BeautifulSoup(source, 'lxml')
            entire = bs.find_all('a', {'id': 'video-title'})
            entireNum = entire[0]
            entireText = entireNum.text.strip()
            musicurl = entireNum.get('href')
            url = 'https://www.youtube.com'+musicurl


        async with ctx.typing(): #봇이 discord 채널에 typing 상태를 표시
            #YTDLSource 메서드로 url에서 오디오 소스를 가져옴
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            #loop=self.bot.loop -> 이벤트 루프를 지정, stream=True -> 스트리밍 모드를 오디오로 가져옴
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
 
        await ctx.send(f'Now playing: {player.title}')
 
    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""
 
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")
 
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")
 
    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""
 
        await ctx.voice_client.disconnect()
        
    @commands.command()
    async def pause(self, ctx):
        ''' 음악을 일시정지 할 수 있습니다. '''
 
        if ctx.voice_client.is_paused() or not ctx.voice_client.is_playing():
            await ctx.send("음악이 이미 일시 정지 중이거나 재생 중이지 않습니다.")
            
        ctx.voice_client.pause()
            
    @commands.command()
    async def resume(self, ctx):
        ''' 일시정지된 음악을 다시 재생할 수 있습니다. '''
 
        if ctx.voice_client.is_playing() or not ctx.voice_client.is_paused():
            await ctx.send("음악이 이미 재생 중이거나 재생할 음악이 존재하지 않습니다.")
            
        ctx.voice_client.resume()

    #play 명령어가 실행되기전에 실행하는 함수
    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()
 
 

 
 
@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("로스트아크"))
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

# @bot.command(aliases=['입장'])
# async def join(ctx):
#     if ctx.author.voice and ctx.author.voice.channel:
#         channel = ctx.author.voice.channel
#         await ctx.send("봇이 {0.author.voice.channel} 채널에 입장합니다.".format(ctx))
#         await channel.connect()
#         print("음성 채널 정보: {0.author.voice}".format(ctx))
#         print("음성 채널 이름: {0.author.voice.channel}".format(ctx))
#     else:
#         await ctx.send("음성 채널에 유저가 존재하지 않습니다. 1명 이상 입장해 주세요.")
 
@bot.command(aliases=['나가기'])
async def out(ctx):
    # await bot.voice_clients[0].disconnect()
    try:
        await ctx.voice_client.disconnect()
        await ctx.send("봇을 {0.author.voice.channel} 에서 내보냈습니다.".format(ctx))
    except IndexError as error_message:
        print(f"에러 발생: {error_message}")
        await ctx.send("{0.author.voice.channel}에 유저가 존재하지 않거나 봇이 존재하지 않습니다.\\n다시 입장후 퇴장시켜주세요.".format(ctx))
    except AttributeError as not_found_channel:
        print(f"에러 발생: {not_found_channel}")
        await ctx.send("봇이 존재하는 채널을 찾는 데 실패했습니다.")
 
 
async def main():
    async with bot:
        await bot.add_cog(Music(bot))
        await bot.start(TOKEN)
 
 
asyncio.run(main())