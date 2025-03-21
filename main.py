import json
import sqlite3
import nextcord
from nextcord.ext import commands

# Загрузка конфигурации
with open('config.json', 'r') as f:
    config = json.load(f)

intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Общие настройки и глобальные переменные
bot.config = config
bot.admin_roles = ["Админ", "Основатель", "Бездушные машины"]
bot.logs_channel = 1148384588800987287
bot.notif_channel = 1042869059378749460
bot.new_lvl_channel = 1168564388194689116
bot.exclude_channels = [909083335064682519, 1042869059378749460, 1168564388194689116, 1057611114126524446,
                        1078383537171996723, 909094954129850418, 909198474061443153, 1155510065508401203,
                        1057604521888579604, 1057454748611137559, 909203930725093416, 909204194697809951,
                        1042868984950820934, 1156421256896319598, 909086509993459742, 909089711501504532,
                        1258808539326058537]
bot.exclude_categories = [1052532014844235816]
bot.lvl_roles = {
    "УРОВЕНЬ 60 - ЛЕГЕНДА": 60,
    "УРОВЕНЬ 30 - БЫВАЛЫЙ ПОДПИСЧИК": 30,
    "УРОВЕНЬ 10 - АКТИВНЫЙ ПОДПИСЧИК": 10,
    "УРОВЕНЬ 1 - МОЛОКОСОС": 1
}

# Подключение баз данных
bot.db_warnings = sqlite3.connect('users.db')
cursor = bot.db_warnings.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INT, username TEXT, warns INT)")
bot.db_warnings.commit()

bot.db_lvl = sqlite3.connect('lvl.db')
lvl_cursor = bot.db_lvl.cursor()
lvl_cursor.execute("CREATE TABLE IF NOT EXISTS users (id INT, username TEXT, lvl INT, messages INT)")
bot.db_lvl.commit()

bot.db_bad_words = sqlite3.connect('bad_words.db')
bad_cursor = bot.db_bad_words.cursor()
bad_cursor.execute("CREATE TABLE IF NOT EXISTS bad_words (id INT, word TEXT)")
bot.db_bad_words.commit()

bot.db_streamers = sqlite3.connect("streamers.db")
streamers_cursor = bot.db_streamers.cursor()
streamers_cursor.execute("CREATE TABLE IF NOT EXISTS streamers (nickname TEXT, status TEXT)")
bot.db_streamers.commit()

# Загрузка аватара
with open("avatar.gif", "rb") as f:
    bot.avatar_data = f.read()

# События, не связанные с конкретным Cog (например, приветствие нового участника)
@bot.event
async def on_ready():
    print(f"{bot.user.name} is ready!")
    await bot.change_presence(
        status=nextcord.Status.online,
        activity=nextcord.Activity(type=nextcord.ActivityType.watching, name="за сервером")
    )
    await bot.user.edit(avatar=bot.avatar_data)

    # Устанавливаем всех стримеров в OFFLINE при старте
    cur = bot.db_streamers.cursor()
    cur.execute("UPDATE streamers SET status = 'OFFLINE'")
    bot.db_streamers.commit()

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(909086509993459742)
    embed = nextcord.Embed(
        title="Добро пожаловать!!",
        description=f"{member.mention} зашел на сервер!",
        color=nextcord.Color.blue()
    )
    await channel.send(embed=embed)
    role = nextcord.utils.get(member.guild.roles, name='Подписчик')
    if role:
        await member.add_roles(role)

# Загрузка расширений (Cogs)
bot.load_extension("cogs.moderation")
bot.load_extension("cogs.leveling")
bot.load_extension("cogs.twitch")
bot.load_extension("cogs.games")
bot.load_extension("cogs.utilities")

bot.run(bot.config['token'])