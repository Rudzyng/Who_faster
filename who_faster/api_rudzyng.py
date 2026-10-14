import os

from flask import request, session
import requests

from constants import API_URL

# сколько секунд ждём ответа портала
TIMEOUT = 10


class ApiError(Exception):
    """Ошибка обращения к API портала (сеть/HTTP/формат ответа)."""


def _capture_game_session() -> tuple[int | None, str | None]:
    """
    Игровая сессия, выданная порталом: (?session=<id>&token=<hmac>).
    Возвращает (gameSessionId, token) или (None, None).
    """
    raw = request.args.get("session") if request else None
    if raw is not None:
        if not raw.isdigit() or int(raw) <= 0:
            raise ApiError("Портал передал некорректный ID игровой сессии.")
        return int(raw), request.args.get("token")
    return session.get("game_session_id"), session.get("game_session_token")


def get_game_session() -> dict | None:
    """Проверяет HMAC и сохраняет профиль пользователя портала."""
    game_session_id, token = _capture_game_session()
    if not game_session_id:
        return None

    try:
        response = requests.post(
            f"{API_URL}/game/session/resolve",
            json={"gameSessionId": game_session_id, "token": token},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ApiError(f"Портал недоступен: {exc}") from exc

    if response.status_code == 401:
        raise ApiError("Портал отклонил подпись игровой сессии.")
    if response.status_code == 404:
        raise ApiError("Игровая сессия не найдена.")
    if response.status_code != 200:
        raise ApiError(f"Ошибка API ({response.status_code}): {response.text}")

    data = response.json()
    if not isinstance(data, dict) or not data.get("valid") or not data.get("userId"):
        raise ApiError("Некорректный ответ API игровой сессии.")
    expected_game_id = os.environ.get("LINGVO_GAME_ID")
    if not expected_game_id or not expected_game_id.isdigit():
        raise ApiError("LINGVO_GAME_ID не настроен для этой игры.")
    if str(data.get("gameId")) != expected_game_id:
        raise ApiError("Игровая сессия выдана для другой игры.")

    session["game_session_id"] = game_session_id
    session["game_session_token"] = token
    session["portal_user_id"] = data["userId"]
    session["portal_user_name"] = data.get("userName") or "Игрок"
    session["portal_total_points"] = data.get("totalUserPoints", 0)
    return data


def post_points(amount: int) -> int:
    """
    Функция, с помощью которой разработчик начисляет баллы пользователю и отправляет их в API рудзынг.
    Работает через игровую сессию портала (?session=...&token=...), когда игра запущена в iframe портала.
    """

    game_session_id, token = _capture_game_session()

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

    points = data.get("newTotalPoints")
    if points is None:
        raise ApiError("Некорректный ответ API.")
    session["portal_total_points"] = points
    return points
