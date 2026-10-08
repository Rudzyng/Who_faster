from typing import List, TypedDict

from flask import request, session
import requests

from constants import API_URL

# сколько секунд ждём ответа портала
TIMEOUT = 10


class Game(TypedDict):
    """
    Объект игры, который возвращается в качестве ответа из API
    """

    gameTitle: str
    gameId: int
    gamePublicationDate: str


class ApiError(Exception):
    """Ошибка обращения к API портала (сеть/HTTP/формат ответа)."""


def get_game_session() -> tuple[int | None, str | None]:
    """
    Игровая сессия, выданная порталом: (?session=<id>&token=<hmac>).
    Возвращает (gameSessionId, token) или (None, None).
    """
    raw = request.args.get("session") if request else None
    if raw is not None and raw.isdigit():
        session["game_session_id"] = int(raw)
        session["game_session_token"] = request.args.get("token")
    return session.get("game_session_id"), session.get("game_session_token")


def get_points() -> int | None:
    """
    Функция, которая обращается к API рудзынг и возвращает количество баллов у игрока
    """

    user_id = session.get("user_id")

    if not user_id:
        raise ApiError("Не записан user_id в сессию.")

    response = requests.get(f"{API_URL}/users/{user_id}/points", timeout=TIMEOUT)

    if response.status_code != 200:
        raise ApiError(f"Ошибка API: {response.text}")

    data = response.json()

    if isinstance(data, int):
        return data
    elif isinstance(data, dict):
        return data.get("points")

    return None


def login(email: str, password: str) -> str:
    """
    Функция, с помощью которой пользователь входит в свой аккаунт и получает свой userId
    """

    user_data = {"email": email, "password": password}

    response = requests.post(
        f"{API_URL}/account/login", json=user_data, timeout=TIMEOUT
    )
    response.raise_for_status()

    data = response.json()
    user_id = None

    if isinstance(data, dict):
        user_id = data.get("userId")

    if not user_id:
        raise Exception("Не удалось получить ID пользователя")

    session["user_id"] = user_id

    return user_id


def post_points(amount: int) -> int:
    """
    Функция, с помощью которой разработчик начисляет баллы пользователю и отправляет их в API рудзынг.
    Работает через игровую сессию портала (?session=...&token=...), когда игра запущена в iframe портала.
    """

    game_session_id, token = get_game_session()

    if not game_session_id:
        raise ApiError("Игра запущена не с портала: сессия не выдана.")

    if amount <= 0:
        raise ApiError("Количество баллов должно быть положительным")

    response = requests.post(
        f"{API_URL}/score",
        json={"gameSessionId": game_session_id, "score": amount, "token": token},
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise ApiError(f"Ошибка API: {response.text}")

    data = response.json()

    return data.get("newTotalPoints")
