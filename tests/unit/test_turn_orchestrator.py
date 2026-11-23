"""Flujo crítico de cierre y liquidación (diagrama de secuencia 1.2) y mitigaciones
de riesgo del E2 (R1, R2, R4, R6, R8)."""
import threading

import pytest

from app.core.deck_card.deck import HAND_SIZE
from app.core.errors import ConcurrencyError, GameRuleError, StaleStateError
from app.core.game_session.snapshot import from_dict, to_dict
from app.core.game_session.state import Phase
from tests.helpers import cards, code


def rig(env, game_id, hands, scores=None):
    """Fija manos/puntajes y deja el turno en p1, fase descartar. Devuelve la versión."""
    state = env.session.cargar(game_id)
    for player, spec in zip(state.players, hands):
        player.hand = cards(spec)
    for player, score in zip(state.players, scores or []):
        player.score = score
    state.turn_index = 0
    state.phase = Phase.DISCARD
    env.store.save(game_id, to_dict(state))
    return state.version


def new_game(env, mode, names, **kw):
    return env.orch.crear_partida(mode, names, seed=kw.pop("seed", 7), **kw)["game_id"]


def current(env, game_id):
    s = env.orch.estado(game_id)
    return s["current_player_id"], s["version"]


# ------------------------------------------------------------------ reparto y turnos
def test_reparto_11_cartas_y_pozo_abierto(env):
    gid = new_game(env, "APUNTADO", ["Ana", "Beto", "Caro"])
    state = env.orch.estado(gid, "p1")
    assert len(state["me"]["hand"]) == HAND_SIZE
    assert state["pile_top"] is not None
    assert state["deck_count"] == 40 - 3 * HAND_SIZE - 1
    assert len(state["room_pin"]) == 6


def test_cuatro_jugadores_usan_dos_barajas(env):
    gid = new_game(env, "CLASICA", ["A", "B", "C", "D"])
    assert env.orch.estado(gid)["deck_count"] == 80 - 4 * HAND_SIZE - 1


def test_no_se_puede_jugar_fuera_de_turno(env):
    gid = new_game(env, "CLASICA", ["A", "B"])
    jugador, version = current(env, gid)
    otro = "p2" if jugador == "p1" else "p1"
    with pytest.raises(GameRuleError):
        env.orch.robar(gid, otro, "mazo", version)


def test_robar_y_descartar_pasa_el_turno_e_incrementa_version(env):
    gid = new_game(env, "CLASICA", ["A", "B"])
    jugador, version = current(env, gid)
    state = env.orch.robar(gid, jugador, "pozo", version)
    assert state["phase"] == "descartar" and state["version"] == version + 1
    carta = state["me"]["hand"][0]["code"]
    state = env.orch.descartar(gid, jugador, carta, state["version"])
    assert state["current_player_id"] != jugador
    assert state["pile_top"]["code"] == carta


# ------------------------------------------------------------------ R2: versión del estado
def test_jugada_con_version_desactualizada_se_rechaza(env):
    gid = new_game(env, "CLASICA", ["A", "B"])
    jugador, version = current(env, gid)
    env.orch.robar(gid, jugador, "mazo", version)
    with pytest.raises(StaleStateError) as err:
        env.orch.robar(gid, jugador, "mazo", version)
    assert err.value.current_version == version + 1


# ------------------------------------------------------------------ ADR-05: cerrojo SET NX
def test_accion_concurrente_se_rechaza_mientras_hay_cerrojo(env):
    gid = new_game(env, "CLASICA", ["A", "B"])
    jugador, version = current(env, gid)
    tomado, liberar = threading.Event(), threading.Event()

    def ocupar():
        with env.store.lock(gid):
            tomado.set()
            liberar.wait(2)

    hilo = threading.Thread(target=ocupar)
    hilo.start()
    tomado.wait(2)
    try:
        with pytest.raises(ConcurrencyError):
            env.orch.robar(gid, jugador, "mazo", version)
    finally:
        liberar.set()
        hilo.join()


# ------------------------------------------------------------------ Clásica
def test_clasica_cierre_valido_gana_la_partida(env):
    gid = new_game(env, "CLASICA", ["A", "B"])
    v = rig(env, gid, ["7o 7c 7e 7b 1o 2o 3o 11c 11e 11b 12o 5c", "1c 2e 3b 4o 5e 6b 10o 10c 12c 12e 6o"])
    result = env.orch.declarar_cierre(gid, "p1", code("5c"), v)
    assert result["valid"]
    assert result["state"]["status"] == "FINISHED"
    assert result["state"]["winners"] == ["A"]
    eventos = [e["event"] for e in env.orch.eventos(gid)]
    assert eventos[-3:] == ["cierre_intentado", "ronda_liquidada", "partida_finalizada"]


def test_cierre_invalido_conserva_turno_mano_y_queda_auditado(env):
    gid = new_game(env, "CLASICA", ["A", "B"])
    v = rig(env, gid, ["7o 7c 7e 1o 2o 3o 11c 11e 11b 12o 4b 5c", "1c 2e 3b 4o 5e 6b 10o 10c 12c 12e 6o"])
    result = env.orch.declarar_cierre(gid, "p1", code("5c"), v)
    assert not result["valid"]
    state = result["state"]
    assert state["status"] == "IN_PROGRESS" and state["phase"] == "descartar"
    assert len(state["me"]["hand"]) == 12 and state["version"] == v
    ultimo = env.orch.eventos(gid)[-1]
    assert ultimo["event"] == "cierre_intentado" and ultimo["data"]["valido"] is False


# ------------------------------------------------------------------ Apuntado
def test_apuntado_liquida_penalizaciones_y_reparte_nueva_ronda(env):
    gid = new_game(env, "APUNTADO", ["A", "B"])
    v = rig(env, gid, ["7o 7c 7e 1o 2o 3o 11c 11e 11b 1b 2c 12e", "4o 4c 4e 12o 12c 1c 2e 3b 5e 6b 10o"])
    result = env.orch.declarar_cierre(gid, "p1", code("12e"), v)
    assert result["valid"], result["cause"]
    state = result["state"]
    assert state["round"] == 2 and state["status"] == "IN_PROGRESS"
    # B: terna de 4s; sobrantes 10+10+1+2+3+5+6+10 = 47
    assert {p["name"]: p["score"] for p in state["players"]} == {"A": 0, "B": 47}


def test_apuntado_llegar_exactamente_a_101_termina_la_partida(env):
    gid = new_game(env, "APUNTADO", ["A", "B", "C"])
    v = rig(env, gid, [
        "7o 7c 7e 1o 2o 3o 11c 11e 11b 1b 2c 12e",
        "4o 4c 4e 5o 6o 7o 10o 11o 12o 1c 5c",  # sobrantes 1 + 5 = 6
        "1e",                                   # sobrante 1
    ], scores=[0, 95, 99])
    state = env.orch.declarar_cierre(gid, "p1", code("12e"), v)["state"]
    assert state["status"] == "FINISHED"
    assert state["losers"] == ["B"]           # 95 + 6 = 101 -> pierde
    assert state["winners"] == ["A"]          # C queda con 100: no pierde
    assert {p["name"]: p["score"] for p in state["players"]} == {"A": 0, "B": 101, "C": 100}


def test_apuntado_100_puntos_no_termina(env):
    gid = new_game(env, "APUNTADO", ["A", "B"])
    v = rig(env, gid, ["7o 7c 7e 1o 2o 3o 11c 11e 11b 1b 2c 12e", "4o 4c 4e 5o 6o 7o 10o 11o 12o 2c 3b"], scores=[0, 95])
    state = env.orch.declarar_cierre(gid, "p1", code("12e"), v)["state"]
    assert {p["name"]: p["score"] for p in state["players"]}["B"] == 100
    assert state["status"] == "IN_PROGRESS"


# ------------------------------------------------------------------ R1 / R6 / Outbox
def test_liquidacion_vuelca_outbox_a_postgres(env):
    gid = new_game(env, "APUNTADO", ["A", "B"])
    v = rig(env, gid, ["7o 7c 7e 1o 2o 3o 11c 11e 11b 1b 2c 12e", "4o 4c 4e 12o 12c 1c 2e 3b 5e 6b 10o"])
    env.orch.declarar_cierre(gid, "p1", code("12e"), v)
    persistidos = [e["event"] for e in env.history.plays(gid)]
    assert "cierre_intentado" in persistidos and "ronda_liquidada" in persistidos
    assert env.store.pending_plays(gid) == []


def test_segundo_cierre_de_la_misma_ronda_se_rechaza(env):
    gid = new_game(env, "APUNTADO", ["A", "B"])
    v = rig(env, gid, ["7o 7c 7e 1o 2o 3o 11c 11e 11b 1b 2c 12e", "4o 4c 4e 12o 12c 1c 2e 3b 5e 6b 10o"])
    viejo = env.store.load(gid)
    env.orch.declarar_cierre(gid, "p1", code("12e"), v)
    env.store.save(gid, viejo)  # simula una segunda petición sobre el estado anterior
    with pytest.raises(ConcurrencyError):
        env.orch.declarar_cierre(gid, "p1", code("12e"), v)


# ------------------------------------------------------------------ R4: reanudación
def test_reanuda_desde_snapshot_si_se_pierde_redis(env):
    gid = new_game(env, "APUNTADO", ["A", "B"])
    antes = env.orch.estado(gid, "p1")
    env.store.flush_state(gid)
    despues = env.orch.estado(gid, "p1")
    assert [c["code"] for c in despues["me"]["hand"]] == [c["code"] for c in antes["me"]["hand"]]
    assert env.orch.eventos(gid)[-1]["event"] == "partida_reanudada"


# ------------------------------------------------------------------ R8: temporizador
def test_turno_vencido_aplica_accion_por_defecto(env):
    gid = new_game(env, "CLASICA", ["A", "B"], turn_seconds=30)
    jugador, version = current(env, gid)
    env.clock.advance(29)
    assert env.orch.expirar_turnos() == 0
    env.clock.advance(2)
    assert env.orch.expirar_turnos() == 1
    state = env.orch.estado(gid)
    assert state["current_player_id"] != jugador and state["version"] == version + 1
    assert env.orch.eventos(gid)[-1]["event"] == "turno_expirado"


def test_sin_temporizador_no_expira(env):
    new_game(env, "CLASICA", ["A", "B"], turn_seconds=0)
    env.clock.advance(10_000)
    assert env.orch.expirar_turnos() == 0


def test_snapshot_ida_y_vuelta(env):
    gid = new_game(env, "APUNTADO", ["A", "B"])
    state = env.session.cargar(gid)
    assert to_dict(from_dict(to_dict(state))) == to_dict(state)
