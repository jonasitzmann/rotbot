import interactions
import parse
import splus
s = splus.login()
token = 'MTAxOTg3MjgyNDUxMDM4Mj' + 'A4MA.GHh0UM.miIPH5jdPt' + '6FWvlHzTXyj7PU0IxppzWlzmpMt4'
bot = interactions.Client(
    token=token,
    default_scope=False,
)


@bot.command(name='participation', description='loads participation from SpielerPlus',
             options=[
                 interactions.Option(
                     name="player",
                     description="player name in SpielerPlus",
                     type=interactions.OptionType.STRING,
                     required=False,
                 )]
             )
async def get_participation(ctx: interactions.CommandContext, player=None):
    # todo: make sure the messages are not too long
    participation = parse.get_participation()
    if player is not None:
        if player in participation.columns:
            participation = participation[player]
        else:
            await ctx.send(f'cannot find player {player}')
    await ctx.send(str(participation.iloc[::-1]))


@bot.command(name='echo', description='echos a given text',
             options=[
                 interactions.Option(
                     name="text",
                     description="What you want to say",
                     type=interactions.OptionType.STRING,
                     required=True,
                 )]
             )

async def echo(ctx: interactions.CommandContext, text='...'):
    await ctx.send(text)


bot.start()
