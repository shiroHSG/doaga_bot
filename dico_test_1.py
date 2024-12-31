import discord, asyncio, datetime
from dico_token import TOKEN
from discord.ext import commands

# 권한설정
intents = discord.Intents.all() # 기본
intents.message_content = True  # 메세지 보내기 허가
intents.voice_states = True # 음성 입장 허가

allowed_guild_ids = [
    341211328909672448,
    973175349473050634,
    1229645113840500786,
    1271315529725902908
]

# 봇 생성
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"), #명령어 시작
    description='간단한 음악 봇',
    intents=intents,
)

# 봇이 준비되었을 때 실행되는 이벤트
@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("!도움 Lost Ark"))
    print(f'{bot.user.name}로 로그인하였습니다.')
    print('------------------------------------')

    print('봇을 추가한 서버 :')
    for guild in bot.guilds:
        print(f'- {guild.name}: {guild.owner} : {guild.id}')
        if guild.id not in allowed_guild_ids:
            if guild.text_channels:
                channel = guild.text_channels[0]  # 첫 번째 텍스트 채널 선택
                await channel.send("내가 언제 추가해도 된댓지?")
            print(f'Leaving server: {guild.name} ({guild.id})')
            await guild.leave()

# 메인 함수 정의 및 봇 실행
async def main():
    async with bot:
        # await bot.add_cog(Music(bot))
        await bot.start(TOKEN)

# asyncio를 이용한 메인 함수 실행
asyncio.run(main())