"""Pruebas funcionales de la API HTTP (estado vivo en memoria + SQLite temporal,
o Redis + PostgreSQL reales si REDIS_URL y DATABASE_URL están definidos)."""
import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_app
from tests.conftest import real_infra_urls


@pytest.fixture()
def client(tmp_path):
    urls = real_infra_urls()
    if urls:
        app = build_app(urls[0], urls[1], run_timer=False)
    else:
        app = build_app(None, f"sqlite:///{tmp_path / 'test.db'}", run_timer=False)
    with TestClient(app) as test_client:
        yield test_client


def create(client, mode="APUNTADO"):
    response = client.post("/api/games", json={"mode": mode, "players": ["Ana", "Beto"], "seed": 4})
    assert response.status_code == 201
    return response.json()


def test_health_y_modalidades(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert {m["id"] for m in client.get("/api/modes").json()} == {"CLASICA", "APUNTADO"}


def test_turno_completo_por_http(client):
    game = create(client)
    gid = game["game_id"]
    state = client.get(f"/api/games/{gid}").json()
    jugador, version = state["current_player_id"], state["version"]

    drawn = client.post(f"/api/games/{gid}/draw", json={"player": jugador, "source": "mazo", "version": version})
    assert drawn.status_code == 200
    body = drawn.json()
    card = body["me"]["hand"][0]["code"]
    discarded = client.post(
        f"/api/games/{gid}/discard", json={"player": jugador, "card": card, "version": body["version"]}
    )
    assert discarded.json()["current_player_id"] != jugador

    events = [e["event"] for e in client.get(f"/api/games/{gid}/events").json()]
    assert events == ["partida_creada", "ronda_iniciada", "robo", "descarte"]


def test_version_desactualizada_devuelve_409_con_version_actual(client):
    gid = create(client)["game_id"]
    state = client.get(f"/api/games/{gid}").json()
    body = {"player": state["current_player_id"], "source": "mazo", "version": state["version"]}
    assert client.post(f"/api/games/{gid}/draw", json=body).status_code == 200
    stale = client.post(f"/api/games/{gid}/draw", json=body)
    assert stale.status_code == 409
    assert stale.json()["current_version"] == state["version"] + 1


def test_fuera_de_turno_devuelve_409(client):
    gid = create(client, "CLASICA")["game_id"]
    state = client.get(f"/api/games/{gid}").json()
    otro = "p2" if state["current_player_id"] == "p1" else "p1"
    response = client.post(f"/api/games/{gid}/draw", json={"player": otro, "source": "mazo", "version": state["version"]})
    assert response.status_code == 409
    assert "turno" in response.json()["detail"]


def test_unirse_por_pin(client):
    game = create(client)
    found = client.get(f"/api/rooms/{game['room_pin']}").json()
    assert found["game_id"] == game["game_id"]


def test_partida_inexistente_404(client):
    assert client.get("/api/games/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/api/rooms/999999x").status_code == 404


def test_modalidad_desconocida_404(client):
    assert client.post("/api/games", json={"mode": "POKER", "players": ["A", "B"]}).status_code == 404


def test_websocket_notifica_cambios(client):
    gid = create(client)["game_id"]
    state = client.get(f"/api/games/{gid}").json()
    with client.websocket_connect(f"/ws/games/{gid}") as ws:
        client.post(f"/api/games/{gid}/draw",
                    json={"player": state["current_player_id"], "source": "mazo", "version": state["version"]})
        assert ws.receive_json() == {"type": "CardDrawn", "version": state["version"] + 1}


def test_cliente_web_servido(client):
    assert "Apuntado" in client.get("/").text
