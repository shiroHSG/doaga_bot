import discord, random, time, asyncio
from discord.ext import commands
#from youtube_dl import YoutubeDL

import yt_dlp
import bs4
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from discord.utils import get
from discord import FFmpegPCMAudio

#컨트롤 클릭이나 f12로 discord 모듈 탐색 가능

#봇 토큰
TOKEN = 'MTIyOTY0Mzg1MzUyNzUxOTI2Mw.GOTqfv.RKzgkAy0QD-l5U1-a8Xy_YYaacuHs6QDG70tDE'

#채널ID
GGUL_CHANNEL_ID = 1229677575912296448   #gul's channel
BOT_CHANNEL_ID = 1233800832093393028    #bot's channel

#권한설정
INTENTS = discord.Intents.all()

#봇 생성
bot = commands.Bot(command_prefix='!', intents = INTENTS)   #커맨드 접두사 설정

#봇이 실행되었을 때
@bot.event   #event는 봇이 실행되는 동안 발생했을때
async def on_ready():   #on_ready 봇이 off->on되엇을때
    print("봇 실행완료")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("로스트아크"))


#봇에게 명령어 내릴때
@bot.command()
async def chat(ctx, *, text):
    await ctx.send(embed = discord.Embed(title="테스트용", description=text, color = 0x00ff00))

@bot.command()
async def 운세(ctx):
    random_value = random.randint(1, 100)
    await ctx.send(f"{ctx.author.mention}님의 운세는: {random_value}!")

@bot.command()
async def join(ctx):
    try:
        global vc
        vc = await ctx.message.author.voice.channel.connect()
    except:
        try:
            await vc.move_to(ctx.message.author.voice.channel)
        except:
            await ctx.send("no user in voice channel")

@bot.command()
async def out(ctx):
    try:
        await vc.disconnect()
    except:
        await ctx.send("bot is not in voice channel")

#음악재생
@bot.command(name="p")
async def play(ctx, *, url):
    YDL_OPTIONS = {'format': 'bestaudio','noplaylist':'True'}
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

    if not vc.is_playing():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
        URL = info['formats'][0]['url']
        vc.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS))
        await ctx.send(embed = discord.Embed(title= "노래 재생", description = "현재 " + url + "을(를) 재생하고 있습니다.", color = 0x00ff00))
    else:
        await ctx.send("노래가 이미 재생되고 있습니다!")

@bot.command()
async def 재생(ctx, *, msg):
    if not vc.is_playing():
        global entireText
        YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True'}
        FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

        #유튜브에서 영상 제목과 링크 등을 가져오는 코드    
        chromedriver_dir = "C:/Users/seong/OneDrive/바탕 화면/디스코드/chromedriver-win64/chromedriver.exe"
        service = Service(executable_path=chromedriver_dir)
        driver = webdriver.Chrome(service=service)
        driver.get("https://www.youtube.com/results?search_query="+msg+"+lyrics")
        source = driver.page_source
        bs = bs4.BeautifulSoup(source, 'lxml')
        entire = bs.find_all('a', {'id': 'video-title'})
        entireNum = entire[0]
        entireText = entireNum.text.strip()
        musicurl = entireNum.get('href')
        url = 'https://www.youtube.com'+musicurl 

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
        URL = info['formats'][0]['url']
        await ctx.send(embed = discord.Embed(title= "노래 재생", description = "현재 " + entireText + "을(를) 재생하고 있습니다.", color = 0x00ff00))
        vc.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS))
    else:
        await ctx.send("이미 노래가 재생 중이라 노래를 재생할 수 없어요!")

@bot.command()
async def 지금노래(ctx):
    if not vc.is_playing():
        await ctx.send("지금은 노래가 재생되지 않네요..")
    else:
        await ctx.send(embed = discord.Embed(title = "지금노래", description = "현재 " + entireText + "을(를) 재생하고 있습니다.", color = 0x00ff00))

#봇 실행
bot.run(TOKEN)








