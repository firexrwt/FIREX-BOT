import requests
import json
from urllib.parse import quote

try:
    with open('config.json') as f:
        config = json.load(f)
except FileNotFoundError:
    print("Ошибка: Файл config.json не найден. Убедитесь, что он существует и содержит необходимые ключи.")
    config = {}


class Stream:
    def __init__(self, title, streamer, game, thumbnail_url):
        self.title = title
        self.streamer = streamer
        self.game = game
        self.thumbnail_url = thumbnail_url

    def __str__(self):
        return (f"Title: {self.title}\n"
                f"Streamer: {self.streamer}\n"
                f"Game: {self.game}\n"
                f"Thumbnail URL: {self.thumbnail_url}")


class ApiError:
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"ApiError: {self.message}"


def getOAuthToken():
    if not all(key in config for key in ['client_id', 'client_secret']):
        print("Ошибка: 'client_id' или 'client_secret' отсутствуют в config.json.")
        raise Exception("Отсутствуют 'client_id' или 'client_secret' в конфигурации.")

    body = {
        "client_id": config['client_id'],
        "client_secret": config['client_secret'],
        "grant_type": "client_credentials"
    }
    try:
        r = requests.post('https://id.twitch.tv/oauth2/token', json=body, timeout=10)  # Добавлен таймаут
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка при запросе OAuth токена: {e}")

    keys = r.json()
    if 'access_token' not in keys:
        raise Exception(f"Не удалось получить 'access_token'. Ответ API: {keys}")
    return keys['access_token']


def checkIfLive(channel):
    if not all(key in config for key in ['client_id']):
        return ApiError("Отсутствует 'client_id' в config.json.")

    try:
        token = getOAuthToken()
    except Exception as e:
        return ApiError(f"Не удалось получить OAuth токен: {str(e)}")

    encoded_channel = quote(channel)
    url = f"https://api.twitch.tv/helix/streams?user_login={encoded_channel}"

    HEADERS = {
        'Client-ID': config['client_id'],
        'Authorization': f'Bearer {token}'
    }

    try:
        req = requests.get(url, headers=HEADERS, timeout=10)

        req.raise_for_status()

        res = req.json()

        if 'data' in res and len(res['data']) > 0:
            data = res['data'][0]
            title = data.get('title', 'No Title')
            streamer = data.get('user_name', 'No Streamer')
            game = data.get('game_name', 'No Game')
            thumbnail_url = data.get('thumbnail_url', 'No Thumbnail').replace('{width}', '1920').replace('{height}',
                                                                                                         '1080')

            if streamer.lower() != channel.lower():
                print(
                    f"Предупреждение: Имя стримера в ответе API ('{streamer}') не совпадает с запрошенным каналом ('{channel}').")

            return Stream(title, streamer, game, thumbnail_url)
        else:
            return "OFFLINE"

    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP ошибка при запросе к Twitch API для канала {channel}: {e.response.status_code} {e.response.text}"
        print(error_message)
        return ApiError(error_message)
    except requests.exceptions.RequestException as e:
        error_message = f"Сетевая ошибка при запросе к Twitch API для канала {channel}: {str(e)}"
        print(error_message)
        return ApiError(error_message)
    except Exception as e:
        error_message = f"Непредвиденная ошибка в checkIfLive для канала {channel}: {str(e)}"
        print(error_message)
        return ApiError(error_message)