import datetime
import nextcord
from nextcord.ext import commands, tasks
from twitch_notifications import checkIfLive

class TwitchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.twitch_notifications_task.start()

    def cog_unload(self):
        self.twitch_notifications_task.cancel()

    @tasks.loop(seconds=120)
    async def twitch_notifications_task(self):
        cur = self.bot.db_streamers.cursor()
        cur.execute('SELECT nickname FROM streamers')
        streamers_list = cur.fetchall()
        for (streamer_nickname,) in streamers_list:
            stream = checkIfLive(streamer_nickname)
            print(str(stream))
            print(f"Статус {streamer_nickname}: {stream}")
            if stream != "OFFLINE":
                cur.execute('SELECT status FROM streamers WHERE nickname = ?', (stream.streamer,))
                result = cur.fetchone()
                print(result[0])
                if result is None or (result and result[0] == "OFFLINE"):
                    cur.execute('UPDATE streamers SET status = "LIVE" WHERE nickname = ?', (stream.streamer,))
                    self.bot.db_streamers.commit()
                    notification = nextcord.Embed(
                        title="Twitch",
                        description=f"Заходите на стрим {stream.streamer} прямо [сейчас](https://www.twitch.tv/{stream.streamer})!!\n",
                        color=nextcord.Color.purple(),
                        timestamp=datetime.datetime.now()
                    )
                    if stream.game == "Just Chatting":
                        notification.add_field(name=stream.title, value="Пока просто общаемся!")
                    else:
                        notification.add_field(name=stream.title, value=f"Стримим {stream.game}!")
                    notification.set_thumbnail(url=stream.thumbnail_url)
                    channel = self.bot.get_channel(self.bot.notif_channel)
                    if channel:
                        await channel.send("@everyone", embed=notification)
            else:
                cur.execute('SELECT status FROM streamers WHERE nickname = ?', (streamer_nickname,))
                result = cur.fetchone()
                if result is not None and result[0] == "LIVE":
                    cur.execute('UPDATE streamers SET status = "OFFLINE" WHERE nickname = ?', (streamer_nickname,))
                    self.bot.db_streamers.commit()

    @nextcord.slash_command(description="Добавляет стримера в список уведомлений.")
    async def add_streamer(self, interaction: nextcord.Interaction, streamer_nickname: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Вы не являетесь администратором, поэтому не можете использовать эту команду!", ephemeral=True)
            return
        cur = self.bot.db_streamers.cursor()
        cur.execute("SELECT nickname FROM streamers WHERE nickname = ?", (streamer_nickname,))
        result = cur.fetchone()
        if result is None:
            cur.execute("INSERT INTO streamers (nickname, status) VALUES (?, ?)", (streamer_nickname, "OFFLINE"))
            self.bot.db_streamers.commit()
            await interaction.response.send_message(f"Стример **{streamer_nickname}** был добавлен в список уведомлений!", ephemeral=True)
        else:
            await interaction.response.send_message(f"Стример **{streamer_nickname}** уже есть в списке уведомлений!", ephemeral=True)

    @nextcord.slash_command(description="Удаляет стримера из списка уведомлений.")
    async def remove_streamer(self, interaction: nextcord.Interaction, streamer_nickname: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Вы не являетесь администратором, поэтому не можете использовать эту команду!", ephemeral=True)
            return
        cur = self.bot.db_streamers.cursor()
        cur.execute("SELECT nickname FROM streamers WHERE nickname = ?", (streamer_nickname,))
        result = cur.fetchone()
        if result is not None:
            cur.execute("DELETE FROM streamers WHERE nickname = ?", (streamer_nickname,))
            self.bot.db_streamers.commit()
            await interaction.response.send_message(f"Стример **{streamer_nickname}** был удален из списка уведомлений!", ephemeral=True)
        else:
            await interaction.response.send_message(f"Стример **{streamer_nickname}** не найден в списке уведомлений!", ephemeral=True)

    @nextcord.slash_command(description="Показывает список всех стримеров, которые есть в списке уведомлений.")
    async def streamers(self, interaction: nextcord.Interaction):
        cur = self.bot.db_streamers.cursor()
        cur.execute("SELECT nickname FROM streamers")
        result = cur.fetchall()
        embed = nextcord.Embed(
            title="Список стримеров",
            description="Список всех стримеров, которые есть в списке уведомлений.",
            color=0x223eff
        )
        for i, row in enumerate(result):
            embed.add_field(name=f"{i+1}. {row[0]}", value=f"Никнейм: {row[0]}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(TwitchCog(bot))