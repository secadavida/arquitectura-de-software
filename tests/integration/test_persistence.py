"""Adaptadores de persistencia (ADR-04 / ADR-05).

Localmente: Redis simulado con fakeredis y PostgreSQL sustituido por SQLite.
En CI (job de integración): Redis 7 y PostgreSQL 16 reales vía REDIS_URL / DATABASE_URL.
"""
import threading

import fakeredis
import pytest
from redis import Redis

from app.core.errors import ConcurrencyError
from app.infrastructure.persistence.postgres_repo import PostgresHistoryStore, create_db_engine
from app.infrastructure.persistence.redis_repo import RedisGameStateStore
from tests.conftest import real_infra_urls

URLS = real_infra_urls()


@pytest.fixture()
def redis_store():
    if URLS:
        client = Redis.from_url(URLS[0], decode_responses=True)
        client.flushdb()
    else:
        client = fakeredis.FakeRedis(decode_responses=True)
    return RedisGameStateStore(client)


@pytest.fixture()
def history(tmp_path):
    url = URLS[1] if URLS else f"sqlite:///{tmp_path / 'hist.db'}"
    return PostgresHistoryStore(create_db_engine(url))


def snapshot(game_id="8a3c8e5e-1111-4222-8333-944455556666", status="IN_PROGRESS", round_number=1, version=0):
    return {
        "id": game_id, "mode_id": "APUNTADO", "room_pin": "123456", "turn_seconds": 60,
        "round_number": round_number, "version": version, "status": status,
        "players": [{"id": "p1", "name": "Ana"}, {"id": "p2", "name": "Beto"}],
    }


def play(event, round_number=1, player="p1", **data):
    return {"ts": "2026-11-23T20:00:00.000001+00:00", "round": round_number, "event": event,
            "player_id": player, "data": data}


# ------------------------------------------------------------------ Redis
def test_redis_guarda_y_lee_estado_y_partidas_activas(redis_store):
    redis_store.save("g1", {"status": "IN_PROGRESS", "x": 1})
    assert redis_store.load("g1") == {"status": "IN_PROGRESS", "x": 1}
    assert "g1" in redis_store.active_games()
    redis_store.deactivate("g1")
    assert "g1" not in redis_store.active_games()


def test_redis_outbox_conserva_orden_y_se_recorta(redis_store):
    for i in range(3):
        redis_store.append_play("g2", {"n": i})
    assert [p["n"] for p in redis_store.pending_plays("g2")] == [0, 1, 2]
    redis_store.clear_plays("g2", 2)
    assert [p["n"] for p in redis_store.pending_plays("g2")] == [2]


def test_redis_set_nx_da_exclusion_mutua(redis_store):
    tomado, liberar = threading.Event(), threading.Event()

    def ocupar():
        with redis_store.lock("g3"):
            tomado.set()
            liberar.wait(2)

    hilo = threading.Thread(target=ocupar)
    hilo.start()
    tomado.wait(2)
    with pytest.raises(ConcurrencyError):
        with redis_store.lock("g3"):
            pass
    liberar.set()
    hilo.join()
    with redis_store.lock("g3"):  # liberado: se puede volver a tomar
        pass


# ------------------------------------------------------------------ PostgreSQL
def test_crear_sesion_y_buscar_por_pin(history):
    snap = snapshot()
    history.create_session(snap, [play("partida_creada", player=None)])
    assert history.find_by_pin("123456") == snap["id"]
    assert history.latest_snapshot(snap["id"])["version"] == 0
    persisted = history.plays(snap["id"])
    assert [p["event"] for p in persisted] == ["partida_creada"]
    assert persisted[0]["ts"].endswith("+00:00")  # las marcas de tiempo conservan UTC


def test_liquidacion_es_atomica_y_rechaza_doble_cierre(history):
    snap = snapshot(game_id="8a3c8e5e-2222-4222-8333-944455556666")
    history.create_session(snap, [])
    after = snapshot(game_id=snap["id"], round_number=2, version=5)
    history.settle_round(snap["id"], 1, "p1", {"p1": 0, "p2": 12}, {"p1": 0, "p2": 12},
                         [play("cierre_intentado", valido=True), play("ronda_iniciada", round_number=2, player=None)],
                         after, next_round=2)
    assert history.latest_snapshot(snap["id"])["version"] == 5
    with pytest.raises(ConcurrencyError):
        history.settle_round(snap["id"], 1, "p1", {"p1": 0, "p2": 12}, {"p1": 0, "p2": 12}, [], after, 2)


def test_fallo_en_la_transaccion_hace_rollback(history):
    snap = snapshot(game_id="8a3c8e5e-3333-4222-8333-944455556666")
    history.create_session(snap, [])
    with pytest.raises(KeyError):
        # jugada de una ronda inexistente: falla dentro de la transacción
        history.settle_round(snap["id"], 1, "p1", {"p1": 0, "p2": 7}, {"p1": 0, "p2": 7},
                             [play("descarte", round_number=99)], snapshot(game_id=snap["id"], version=9), 2)
    assert history.latest_snapshot(snap["id"])["version"] == 0  # nada quedó confirmado
    # la ronda sigue abierta y puede liquidarse correctamente
    history.settle_round(snap["id"], 1, "p1", {"p1": 0, "p2": 7}, {"p1": 0, "p2": 7}, [],
                         snapshot(game_id=snap["id"], version=9), 2)
