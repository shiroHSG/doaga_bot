import discord, asyncio, datetime
import dico_var
from dico_var import TOKEN
import json
from discord.ext import commands
import yt_dlp as youtube_dl

JSON_FILE = 'dico_allowed_ch.json'
youtube_dl.utils.bug_reports_message = lambda: ''
intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True  # voice_state를 활성화합니다.

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

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description='간단한 음악 봇',
    intents=intents,
)

def is_allowed_channel(ctx):
    allowed_channels = load_allowed_channels()
    return ctx.channel.id in allowed_channels

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
    'source_address': '0.0.0.0',  # IPv4로 바인딩
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

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
        if 'entries' in info:
            url = info['entries'][0]['webpage_url']
        else:
            url = info['webpage_url']
        return url

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}         # {guild_id: [url1, url2, ...]}
        self.playing = {}        # {guild_id: True/False}
        self.current_song = {}   # {guild_id: YTDLSource 객체}
    
    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    async def play_next(self, ctx):
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)

        if queue:
            url = queue.pop(0)
            async with ctx.typing():
                player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                ctx.voice_client.play(
                    player,
                    after=lambda e: self.bot.loop.create_task(
                        self.play_next(ctx)
                    ) if e is None else print(f'플레이어 에러: {e}')
                )

            # 현재 곡 정보 저장
            self.current_song[guild_id] = player

            embed = discord.Embed(title="현재 재생 중", description=f"[{player.title}]({player.url})", color=discord.Color.blue())
            embed.set_thumbnail(url=player.data.get('thumbnail'))
            duration = str(datetime.timedelta(seconds=int(player.duration)))
            embed.add_field(name="재생 시간", value=duration, inline=True)
            embed.add_field(name="신청자", value=ctx.author.mention, inline=True)
            await ctx.send(embed=embed)
        else:
            self.playing[guild_id] = False
            # 재생이 끝나면 current_song에서도 제거
            if guild_id in self.current_song:
                del self.current_song[guild_id]

    async def play(self, ctx, query):
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)

        if query.startswith("http://") or query.startswith("https://"):
            url = query
        else:
            url = await YTDLSource.from_query(query, loop=self.bot.loop)

        queue.append(url)

        if not self.playing.get(guild_id, False):
            self.playing[guild_id] = True
            await self.play_next(ctx)

    @commands.command(name="p")
    async def play_command(self, ctx, *, query):
        await ctx.message.delete()
        await self.play(ctx, query)

    @commands.command()
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("음성 채널에 연결되어 있지 않습니다.")
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"볼륨을 {volume}%로 조절하였습니다.")
        await ctx.message.delete()

    @commands.command()
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()
        await ctx.message.delete()

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client is None:
            return
        if ctx.voice_client.is_paused() or not ctx.voice_client.is_playing():
            await ctx.send("음악이 이미 일시 정지되었거나 재생 중인 곡이 없습니다.")
        else:
            ctx.voice_client.pause()
        await ctx.message.delete()

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client is None:
            return
        if ctx.voice_client.is_playing() or not ctx.voice_client.is_paused():
            await ctx.send("음악이 이미 재생 중이거나 다시 재생할 곡이 없습니다.")
        else:
            ctx.voice_client.resume()
        await ctx.message.delete()

    @commands.command(name="skip")
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()  # 곡이 stop되면 after 콜백으로 play_next가 호출됨
        else:
            await ctx.send("건너뛸 곡이 없습니다.")
        await ctx.message.delete()

    @play_command.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                print(f"{ctx.author.voice.channel}에 연결합니다.")
                await ctx.author.voice.channel.connect()
            else:
                msg = await ctx.send("음성 채널에 연결되어 있지 않습니다.")
                await asyncio.sleep(2)
                await msg.delete()
                raise commands.CommandError("작성자가 음성 채널에 연결되어 있지 않습니다.")
        elif not ctx.voice_client.is_playing():
            guild_id = ctx.guild.id
            if self.queues.get(guild_id):
                await self.play_next(ctx)

    # ============== 추가된 부분 ==============
    @commands.command(name="nowplaying", aliases=["현재노래", "np"])
    async def now_playing_command(self, ctx):
        """현재 재생중인 곡 정보를 보여줍니다."""
        guild_id = ctx.guild.id
        
        if not self.playing.get(guild_id, False):
            return await ctx.send("지금 재생 중인 곡이 없습니다.")
        
        player = self.current_song.get(guild_id)
        if not player:
            return await ctx.send("지금 재생 중인 곡 정보가 없습니다.")
        
        title = player.title
        url = player.url
        duration = player.duration
        thumbnail = player.data.get('thumbnail')

        embed = discord.Embed(
            title="현재 재생 중",
            description=f"[{title}]({url})",
            color=discord.Color.green()
        )
        
        if duration:
            duration_str = str(datetime.timedelta(seconds=int(duration)))
            embed.add_field(name="재생 시간", value=duration_str, inline=True)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        await ctx.send(embed=embed)


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("!사용법 로스트아크"))
    print(f'{bot.user}로 로그인하였습니다.')
    print('------------')

    print('봇을 추가한 서버 :')
    for guild in bot.guilds:
        print(f'- {guild.name}: {guild.id}')
        if guild.id not in dico_var.allowed_guild_ids:
            if guild.text_channels:
                channel = guild.text_channels[0]  # 첫 번째 텍스트 채널 선택
                await channel.send("내가 언제 추가해도 된댓지?")
            print(f'Leaving server: {guild.name} ({guild.id})')
            await guild.leave()

@bot.event
async def on_guild_join(guild):
    print(f'Joined new server: {guild.name} ({guild.id})')

    if guild.id not in dico_var.allowed_guild_ids:
        if guild.text_channels:
            channel = guild.text_channels[0]
            await channel.send("추가 안됩니당")
        print(f'Leaving server: {guild.name} ({guild.id})')
        await guild.leave()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    ctx = await bot.get_context(message)

    allowed_channels = load_allowed_channels()
    if message.channel.id in allowed_channels and ctx.command is None:
        cog = bot.get_cog("Music")
        query = message.content

        await message.delete()

        # 봇이 음성 채널에 연결되어 있지 않은 경우
        if ctx.voice_client is None:
            if message.author.voice:
                await message.author.voice.channel.connect()
            else:
                msg = await ctx.send("You are not connected to a voice channel.")
                await asyncio.sleep(2)
                await msg.delete()
                return
        
        await cog.play(ctx, query=query)
    
    await bot.process_commands(message)

@bot.command(aliases=['도움'])
async def command_list(ctx):
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

@bot.command(aliases=['채널추가'])
async def allow_channel(ctx):
    await ctx.message.delete()
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

@bot.command(aliases=['leave'])
async def out(ctx):
    try:
        await ctx.voice_client.disconnect()
        cog = bot.get_cog("Music")
        if cog:
            guild_id = ctx.guild.id
            # 해당 서버의 큐 초기화
            if guild_id in cog.queues:
                cog.queues[guild_id] = []
            if guild_id in cog.playing:
                cog.playing[guild_id] = False
    except AttributeError:
        await ctx.send(f"봇이 존재하는 채널을 찾는 데 실패했습니다.")
    except Exception as e:
        await ctx.send(f"에러 발생: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    # 봇이 음성 채널에서 퇴장했을 때 (강제로 이동되거나 끊긴 경우 등)
    if member == bot.user and before.channel is not None and after.channel is None:
        print("봇이 음성 채널에서 퇴장했습니다. 모든 정보를 초기화합니다.")

        cog = bot.get_cog("Music")
        if cog:
            guild_id = before.channel.guild.id
            cog.queues[guild_id] = []
            cog.playing[guild_id] = False

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

async def main():
    async with bot:
        await bot.add_cog(Music(bot))
        await bot.start(TOKEN)

asyncio.run(main())
