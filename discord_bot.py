import interactions
import parse
import splus
s = splus.login()
token = 'MTAxOTg3MjgyNDUxMDM4Mj' + 'A4MA.GHh0UM.miIPH5jdPt' + '6FWvlHzTXyj7PU0IxppzWlzmpMt4'
bot = interactions.Client(
    token=token,
    default_scope=False,
)


@bot.command(name='participation', description='loads participation from SpielerPlus',)
async def get_participation(ctx: interactions.CommandContext):
    # todo: make sure the messages are not too long
    participation = str(parse.get_participation())
    await ctx.send(str(participation))


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
