import discord, asyncio, datetime, pytz, random

TOKEN = 'MTIyOTY0Mzg1MzUyNzUxOTI2Mw.GOTqfv.RKzgkAy0QD-l5U1-a8Xy_YYaacuHs6QDG70tDE'
INTENTS = discord.Intents.all()
GGUL_CHANNEL_ID = 1229677575912296448   #gul's channel
BOT_CHANNEL_ID = 1233800832093393028    #bot's channel

client = discord.Client(intents = INTENTS)

# 클라이언트 생성
@client.event   #event는 봇이 실행되는 동안 발생했을때
async def on_ready():   #on_ready 봇이 off->on되엇을때
    await client.change_presence(status=discord.Status.online, activity=discord.Game("로스트아크"))


@client.event
async def on_message(message):  #어떤 메세지라도 입력되면 실행
    if message.author == client.user:   #본인의 메세지는 제외
        return
    if message.content == "테스트":  #메세지 내용이 테스트 일경우 message.author=글쓴이, mention=언급
        await message.channel.send("{}님 안녕하세요!".format(message.author.mention))    #메세지가 작성된 채널에 메세지 전송
        await message.author.send("{}님께 보내는 dm이에요!".format(message.author))    #메세지 작성자에게 dm
        #특정채널에 입력보내기
    if message.content == "특정입력":
        ch = client.get_channel(GGUL_CHANNEL_ID)
        await ch.send("특정입력 보내기")

    if message.content == '!전체삭제':
    # 채널의 메시지를 전부 가져와서 삭제
        async for msg in message.channel.history(limit=None):
            await msg.delete()

    if message.content == "!운세":
        await message.delete()
        random_value = random.randint(1, 100)
        random_value_str = str(random_value)
        ch = client.get_channel(BOT_CHANNEL_ID)
        await ch.send ("{}님의 운세는 : ".format(message.author)+random_value_str+"!")

    #임베드 출력
    if message.content == "음악": # 메세지 감지
        embed = discord.Embed(title="노래를 추가했어요", description="#",timestamp=datetime.datetime.now(pytz.timezone('UTC')), color=0x00ff00)

        embed.add_field(name="곡 길이", value="시간 소스 따오기", inline=True)
        #inline은 한줄로 생각
        embed.add_field(name="대기열", value="대기열 소스 따오기", inline=True)
        embed.add_field(name="음원", value="링크 따오기", inline=True)

        # embed.set_footer(text="신청자 이름 따오기", icon_url="신청자 이미지 소스따오기")
        # embed.set_thumbnail(url="음원 섬네일 따오기")
        await message.channel.send (embed=embed)

    #공지출력
    if message.content.startswith ("!공지"):    #!로 시작하면 실행
        await message.channel.purge(limit=1)    #리미트 숫자만큼 메세지를 삭제함
        i = (message.author.guild_permissions.administrator)    #서버 관리자 권한 허가가 있는지
        if i is True:   #권한이 있을 경우
            notice = message.content[4:]    #메세지 내용 5번째부터 끝까지 담기
            channel = client.get_channel(GGUL_CHANNEL_ID)
            embed = discord.Embed(title="**공지사항 제목 (볼드)*", description="\n――――――――――――――――――――――――――――\n\n{}\n\n――――――――――――――――――――――――――――".format(notice),timestamp=datetime.datetime.now(pytz.timezone('UTC')), color=0x00ff00)
            embed.set_footer(text="Bot Made by. 바코드 #1741 | 담당 관리자 : {}".format(message.author))#, icon_url="이미지 링크"
            # embed.set_thumbnail(url="이미지 링크")
            await message.channel.send ("@everyone", embed=embed)
            await message.author.send("*[ BOT 자동 알림 ]* | 정상적으로 공지가 채널에 작성이 완료되었습니다 : )\n\n[ 기본 작성 설정 채널 ] : {}\n[ 공지 발신자 ] : {}\n\n[ 내용 ]\n{}".format(channel, message.author, notice))
 
        if i is False:  #권한이 없을 경우
            await message.channel.send("{}, 당신은 관리자가 아닙니다".format(message.author.mention))
    

    if message.content.startswith ("!도움"):
        await message.delete()
        await message.author.send("아직 별로 구현된게 없어요 \n !운세 운세를 알려줘요 \n !요청 (요청사항) 요청사항을 저장할 수 있어요 \n !목록 요청한 목록을 알 수 있어요")

# 봇 실행
client.run(TOKEN)








