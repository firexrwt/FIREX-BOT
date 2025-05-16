import datetime
import nextcord
from nextcord.ext import commands, tasks
from twitch_notifications import checkIfLive, Stream, ApiError


class TwitchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.twitch_notifications_task.start()

    def cog_unload(self):
        self.twitch_notifications_task.cancel()

    @tasks.loop(seconds=120)
    async def twitch_notifications_task(self):
        if not hasattr(self.bot, 'db_streamers') or self.bot.db_streamers is None:
            print("Ошибка: База данных стримеров (self.bot.db_streamers) не инициализирована в TwitchCog.")
            return

        cur = self.bot.db_streamers.cursor()
        try:
            cur.execute('SELECT nickname FROM streamers')
            streamers_list = cur.fetchall()
        except Exception as e:
            print(f"Ошибка при получении списка стримеров из БД: {e}")
            return

        for (streamer_nickname,) in streamers_list:

            stream_status_or_error = checkIfLive(streamer_nickname)

            if isinstance(stream_status_or_error, Stream):
                print(f"Статус {streamer_nickname} (API): LIVE - {stream_status_or_error.title}")
            elif isinstance(stream_status_or_error, ApiError):
                print(f"Статус {streamer_nickname} (API): Ошибка - {str(stream_status_or_error)}")
            else:  # Должно быть "OFFLINE"
                print(f"Статус {streamer_nickname} (API): {str(stream_status_or_error)}")

            if isinstance(stream_status_or_error, Stream):
                stream = stream_status_or_error
                try:
                    cur.execute('SELECT status FROM streamers WHERE nickname = ?', (stream.streamer,))
                    result = cur.fetchone()
                except Exception as e:
                    print(f"Ошибка при запросе статуса стримера {stream.streamer} из БД: {e}")
                    continue

                if result is None or (result and result[0] == "OFFLINE"):
                    try:
                        cur.execute('UPDATE streamers SET status = "LIVE" WHERE nickname = ?', (stream.streamer,))
                        self.bot.db_streamers.commit()
                        print(f"Статус {stream.streamer} обновлен на LIVE в БД. Отправка уведомления.")
                    except Exception as e:
                        print(f"Ошибка при обновлении статуса на LIVE для {stream.streamer} в БД: {e}")
                        continue

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

                    channel_id = self.bot.notif_channel
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        try:
                            await channel.send("@everyone", embed=notification)
                        except Exception as e:
                            print(f"Ошибка при отправке уведомления в Discord для {stream.streamer}: {e}")
                    else:
                        print(f"Ошибка: Канал для уведомлений (ID: {channel_id}) не найден.")

            elif stream_status_or_error == "OFFLINE":
                try:
                    cur.execute('SELECT status FROM streamers WHERE nickname = ?', (streamer_nickname,))
                    result = cur.fetchone()
                except Exception as e:
                    print(f"Ошибка при запросе статуса стримера {streamer_nickname} из БД (при обработке OFFLINE): {e}")
                    continue

                if result is not None and result[0] == "LIVE":
                    try:
                        cur.execute('UPDATE streamers SET status = "OFFLINE" WHERE nickname = ?', (streamer_nickname,))
                        self.bot.db_streamers.commit()
                        print(f"Статус {streamer_nickname} обновлен на OFFLINE в БД.")
                    except Exception as e:
                        print(f"Ошибка при обновлении статуса на OFFLINE для {streamer_nickname} в БД: {e}")

            elif isinstance(stream_status_or_error, ApiError):
                pass

            else:
                print(f"Неожиданный результат от checkIfLive для {streamer_nickname}: {str(stream_status_or_error)}")

    @twitch_notifications_task.before_loop
    async def before_twitch_notifications_task(self):
        await self.bot.wait_until_ready()

    # Остальные команды без изменений
    @nextcord.slash_command(description="Добавляет стримера в список уведомлений.")
    async def add_streamer(self, interaction: nextcord.Interaction, streamer_nickname: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Вы не являетесь администратором, поэтому не можете использовать эту команду!", ephemeral=True)
            return

        if not hasattr(self.bot, 'db_streamers') or self.bot.db_streamers is None:
            await interaction.response.send_message("Ошибка: База данных стримеров не инициализирована.",
                                                    ephemeral=True)
            print("Ошибка: База данных стримеров (self.bot.db_streamers) не инициализирована в add_streamer.")
            return

        cur = self.bot.db_streamers.cursor()
        try:
            cur.execute("SELECT nickname FROM streamers WHERE nickname = ?", (streamer_nickname,))
            result = cur.fetchone()
            if result is None:
                cur.execute("INSERT INTO streamers (nickname, status) VALUES (?, ?)",
                            (streamer_nickname, "OFFLINE"))  # Изначально OFFLINE
                self.bot.db_streamers.commit()
                await interaction.response.send_message(
                    f"Стример **{streamer_nickname}** был добавлен в список уведомлений!", ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"Стример **{streamer_nickname}** уже есть в списке уведомлений!", ephemeral=True)
        except Exception as e:
            print(f"Ошибка при добавлении стримера {streamer_nickname} в БД: {e}")
            await interaction.response.send_message(f"Произошла ошибка при добавлении стримера {streamer_nickname}.",
                                                    ephemeral=True)

    @nextcord.slash_command(description="Удаляет стримера из списка уведомлений.")
    async def remove_streamer(self, interaction: nextcord.Interaction, streamer_nickname: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Вы не являетесь администратором, поэтому не можете использовать эту команду!", ephemeral=True)
            return

        if not hasattr(self.bot, 'db_streamers') or self.bot.db_streamers is None:
            await interaction.response.send_message("Ошибка: База данных стримеров не инициализирована.",
                                                    ephemeral=True)
            print("Ошибка: База данных стримеров (self.bot.db_streamers) не инициализирована в remove_streamer.")
            return

        cur = self.bot.db_streamers.cursor()
        try:
            cur.execute("SELECT nickname FROM streamers WHERE nickname = ?", (streamer_nickname,))
            result = cur.fetchone()
            if result is not None:
                cur.execute("DELETE FROM streamers WHERE nickname = ?", (streamer_nickname,))
                self.bot.db_streamers.commit()
                await interaction.response.send_message(
                    f"Стример **{streamer_nickname}** был удален из списка уведомлений!", ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"Стример **{streamer_nickname}** не найден в списке уведомлений!", ephemeral=True)
        except Exception as e:
            print(f"Ошибка при удалении стримера {streamer_nickname} из БД: {e}")
            await interaction.response.send_message(f"Произошла ошибка при удалении стримера {streamer_nickname}.",
                                                    ephemeral=True)

    @nextcord.slash_command(description="Показывает список всех стримеров, которые есть в списке уведомлений.")
    async def streamers(self, interaction: nextcord.Interaction):
        if not hasattr(self.bot, 'db_streamers') or self.bot.db_streamers is None:
            await interaction.response.send_message("Ошибка: База данных стримеров не инициализирована.",
                                                    ephemeral=True)
            print("Ошибка: База данных стримеров (self.bot.db_streamers) не инициализирована в streamers.")
            return

        cur = self.bot.db_streamers.cursor()
        try:
            cur.execute("SELECT nickname, status FROM streamers")
            result = cur.fetchall()
            embed = nextcord.Embed(
                title="Список стримеров",
                description="Список всех стримеров в базе уведомлений и их текущий известный статус.",
                color=0x223eff
            )
            if not result:
                embed.description = "В списке уведомлений пока нет ни одного стримера."
            for i, row in enumerate(result):
                nickname = row[0]
                status = row[1] if row[1] else "Неизвестно"
                embed.add_field(name=f"{i + 1}. {nickname}", value=f"Статус: {status}", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Ошибка при получении списка стримеров из БД для команды /streamers: {e}")
            await interaction.response.send_message("Произошла ошибка при получении списка стримеров.", ephemeral=True)


def setup(bot):
    bot.add_cog(TwitchCog(bot))