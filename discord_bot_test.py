import discord
import asyncio
import datetime
from dico_var import TOKEN
import json
from discord.ext import commands
import yt_dlp as youtube_dl

allowed_guild_ids = [
    341211328909672448,
    973175349473050634,
    1229645113840500786,
    1271315529725902908
]

JSON_FILE = 'dico_allowed_ch.json'

def load_allowed_channels():
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
        return data.get('allowed_channels', [])

def save_allowed_channels(allowed_channels):
    data = {
        'allowed_channels': allowed_channels
    }
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True  # voice_state를 활성화합니다.

# 봇 생성
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description='간단한 음악 봇',
    intents=intents,
)

# 허용된 채널 확인 함수
def is_allowed_channel(ctx):
    allowed_channels = load_allowed_channels()
    return ctx.channel.id in allowed_channels

# YouTube DL 설정
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
    'source_address': '0.0.0.0',  # IPv4로 바인딩 (IPv6 문제 회피)
}

# FFmpeg 옵션
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# YouTube DL 객체 생성
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# 음악 소스 클래스 정의
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.1):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

    @classmethod
    async def from_query(cls, query, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        url = info['entries'][0]['webpage_url'] if 'entries' in info else info['webpage_url']
        return url

# 음악 관련 기능을 담당하는 코그 클래스
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.playing = False

    # 음성 채널에 들어가는 기능
    @commands.command()
    async def join(self, ctx):
        """음성 채널에 들어갑니다."""
        channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    # 다음 곡 재생하는 기능
    async def play_next(self, ctx):
        print(f"봇이 활동중인 서버: {ctx.guild.name}")
        if self.queue:
            url = self.queue.pop(0)
            async with ctx.typing():
                player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                ctx.voice_client.play(player, after=lambda e: self.bot.loop.create_task(self.play_next(ctx)) if e is None else print(f'플레이어 에러: {e}'))
            
            embed = discord.Embed(title="현재 재생 중", description=f"[{player.title}]({player.url})", color=discord.Color.blue())
            embed.set_thumbnail(url=player.data.get('thumbnail'))
            duration = str(datetime.timedelta(seconds=int(player.duration)))
            embed.add_field(name="재생 시간", value=duration, inline=True)
            embed.add_field(name="신청자", value=ctx.author.mention, inline=True)
            await ctx.send(embed=embed)
        else:
            self.playing = False

    # 음악 추가 및 재생하는 기능
    async def play(self, ctx, query):
        if query.startswith("http://") or query.startswith("https://"):
            url = query
        else:
            url = await YTDLSource.from_query(query, loop=self.bot.loop)
        self.queue.append(url)
        if not self.playing:
            self.playing = True
            await self.play_next(ctx)

    # 음악 재생 명령어 처리
    @commands.command(name="p")
    async def play_command(self, ctx, *, query):
        await ctx.message.delete()  # 입력된 명령어 메시지 삭제
        await self.play(ctx, query)

    # 음악 볼륨 조절 기능
    @commands.command()
    async def volume(self, ctx, volume: int):
        """볼륨을 조절합니다."""
        if ctx.voice_client is None:
            return await ctx.send("음성 채널에 연결되어 있지 않습니다.")
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"볼륨을 {volume}%로 조절하였습니다.")
        await ctx.message.delete()  # 입력된 명령어 메시지 삭제

    # 음악 정지 및 음성 채널 나가기 기능
    @commands.command()
    async def stop(self, ctx):
        """음성 채널에서 봇을 정지하고 나갑니다."""
        await ctx.voice_client.disconnect()
        await ctx.message.delete()  # 입력된 명령어 메시지 삭제

    # 봇이 음성 채널에서 정지하는 기능
    @commands.command()
    async def pause(self, ctx):
        """현재 재생 중인 곡을 일시 정지합니다."""
        if ctx.voice_client.is_paused() or not ctx.voice_client.is_playing():
            await ctx.send("음악이 이미 일시 정지되었거나 재생 중인 곡이 없습니다.")
        else:
            ctx.voice_client.pause()
        await ctx.message.delete()  # 입력된 명령어 메시지 삭제

    # 일시 정지된 곡 다시 재생하는 기능
    @commands.command()
    async def resume(self, ctx):
        """일시 정지된 곡을 다시 재생합니다."""
        if ctx.voice_client.is_playing() or not ctx.voice_client.is_paused():
            await ctx.send("음악이 이미 재생 중이거나 다시 재생할 곡이 없습니다.")
        else:
            ctx.voice_client.resume()
        await ctx.message.delete()  # 입력된 명령어 메시지 삭제

    # 현재 곡 건너뛰기 기능
    @commands.command(name="skip")
    async def skip(self, ctx):
        """현재 재생 중인 곡을 건너뜁니다."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        else:
            await ctx.send("건너뛸 곡이 없습니다.")
        await ctx.message.delete()  # 입력된 명령어 메시지 삭제

    # 음악 재생 전에 음성 채널 연결 확인
    @play_command.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                print(ctx.author.voice.channel)
                await ctx.author.voice.channel.connect()
            else:
                msg = await ctx.send("음성 채널에 연결되어 있지 않습니다.")
                await asyncio.sleep(2)
                await msg.delete()
                raise commands.CommandError("작성자가 음성 채널에 연결되어 있지 않습니다.")
        elif not ctx.voice_client.is_playing():
            if self.queue:
                await self.play_next(ctx)

# 봇이 준비되었을 때 실행되는 이벤트
@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("!사용법 로스트아크"))
    print(f'{bot.user}로 로그인하였습니다.')
    print('------------')

    # 서버 목록 출력
    print('봇을 추가한 서버 :')
    for guild in bot.guilds:
        print(f'- {guild.name}: {guild.id}')
        if guild.id not in allowed_guild_ids:
            if guild.text_channels:
                channel = guild.text_channels[0]  # 첫 번째 텍스트 채널 선택
                await channel.send("내가 언제 추가해도 된댓지?")
            print(f'Leaving server: {guild.name} ({guild.id})')
            await guild.leave()

@bot.event
async def on_guild_join(guild):
    print(f'Joined new server: {guild.name} ({guild.id})')

    if guild.id not in allowed_guild_ids:
        # 첫 번째 텍스트 채널에 메시지를 남김
        if guild.text_channels:
            channel = guild.text_channels[0]  # 첫 번째 텍스트 채널 선택
            await channel.send("추가 안됩니당")

        print(f'Leaving server: {guild.name} ({guild.id})')
        await guild.leave()

# 메시지 이벤트 처리
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    ctx = await bot.get_context(message)
    # 메시지가 허용된 채널에서 왔고 명령어가 아닌 경우
    allowed_channels = load_allowed_channels()
    if message.channel.id in allowed_channels and ctx.command is None:
        cog = bot.get_cog("Music")

        query=message
        await message.delete()
        
        # 봇이 음성 채널에 연결되어 있지 않은 경우
        
        if ctx.voice_client is None:
            if ctx.author.voice:  # 메시지 작성자가 음성 채널에 있는 경우
                await ctx.author.voice.channel.connect()
            else:
                msg = await ctx.send("You are not connected to a voice channel.")
                await asyncio.sleep(2)
                await msg.delete()
                return  # 작성자가 음성 채널에 없으면 종료
                
        await cog.play(ctx, query=query.content)
        
    await bot.process_commands(message)

@bot.command(aliases=['사용법'])
async def commands(ctx):
    await ctx.message.delete()

    help_embed = discord.Embed(title="노래하는 도아가 설명",
                               description="도아가 봇의 사용법 및 설명입니다.",
                               color=discord.Color.blue())

    help_embed.add_field(name="!join", value="봇을 음성 채널에 입장시킵니다.", inline=False)
    help_embed.add_field(name="!out", value="봇을 음성 채널에서 퇴장시킵니다.", inline=False)
    help_embed.add_field(name="!p url", value="지정한 URL의 음악을 재생합니다.", inline=False)
    help_embed.add_field(name="!p 노래", value="지정한 제목의 노래를 검색하여 재생합니다.", inline=False)
    help_embed.add_field(name="!채널추가", value="명령어 없이 입력한 채널을 허용 채널로 추가합니다.", inline=False)
    help_embed.add_field(name="!pause", value="현재 재생 중인 곡을 일시 정지합니다.", inline=False)
    help_embed.add_field(name="!resume", value="일시 정지된 곡을 다시 재생합니다.", inline=False)
    help_embed.add_field(name="!skip", value="현재 재생 중인 곡을 건너뜁니다.", inline=False)
    help_embed.add_field(name="기타", value="봇은 반드시 !out 명령어로 퇴장시켜야하며, 강제 종료 시, 2분을 기다려야 합니다.", inline=False)
    help_embed.add_field(name="미완성", value="개발 단계라 노래 추가시 잔렉이 발생합니다.", inline=False)

    await ctx.author.send(embed=help_embed)

# 채널을 허용하는 명령어
@bot.command(aliases=['채널추가'])
async def allow_channel(ctx):
    await ctx.message.delete()
    """현재 채널 ID를 ALLOWED_CHANNEL_ID에 추가합니다."""
    channel_id = ctx.channel.id
    
    allowed_channels = load_allowed_channels()
    if channel_id not in allowed_channels:
        allowed_channels.append(channel_id)
        save_allowed_channels(allowed_channels)
        msg = await ctx.send(f"채널 ID {channel_id}가 허용된 채널에 추가되었습니다.")
        await asyncio.sleep(2)
        await msg.delete()
    else:
        msg = await ctx.send("이 채널은 이미 허용된 채널입니다.")
        await asyncio.sleep(2)
        await msg.delete()

# 음성 채널에서 봇을 나가는 명령어
@bot.command(aliases=['leave'])
async def out(ctx):
    try:
        await ctx.voice_client.disconnect()
        cog = bot.get_cog("Music")
        cog.queue = []
        cog.playing = False
    except AttributeError:
        await ctx.send(f"봇이 존재하는 채널을 찾는 데 실패했습니다.")
    except Exception as e:
        await ctx.send(f"에러 발생: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and before.channel is not None and after.channel is None:
        print("봇이 음성 채널에서 퇴장했습니다. 모든 정보를 초기화합니다.")
        
        # Music Cog를 가져옵니다. 만약 Cog가 없으면 None을 반환합니다.
        cog = bot.get_cog("Music")
        if cog:
            # 큐를 초기화합니다.
            cog.queue = []
            # 현재 재생 상태를 초기화합니다.
            cog.playing = False
            
            # 음성 클라이언트가 연결되어 있다면 음성 연결을 끊습니다.
            for vc in bot.voice_clients:
                if vc.guild == before.channel.guild:
                    try:
                        print(f"{vc.guild.name}에서 음성 연결을 끊는 중...")
                        await vc.disconnect(force=True)
                        print(f"{vc.guild.name}에서 음성 연결이 성공적으로 끊어졌습니다.")
                    except Exception as e:
                        print(f"{vc.guild.name}에서 음성 연결을 끊는 중 오류 발생: {e}")
        else:
            print("Music Cog를 찾을 수 없습니다.")
# 메인 함수 정의 및 봇 실행
async def main():
    async with bot:
        await bot.add_cog(Music(bot))
        await bot.start(TOKEN)

# asyncio를 이용한 메인 함수 실행
asyncio.run(main())
