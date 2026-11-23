"""Casos borde exigidos por el Testing Checklist del Entregable 3."""
import pytest

from app.bootstrap import build_registry
from app.core.rule_engine.registry import GameModeRegistry
from app.core.rule_engine.regla_apuntado import ReglaApuntadoStrategy
from app.core.rule_engine.regla_clasica import ReglaClasicaStrategy
from tests.helpers import cards

CLASSIC = ReglaClasicaStrategy()
APUNTADO = ReglaApuntadoStrategy()


# ----------------------------------------------------------------- Clásica
def test_classic_valid_cuarta_two_ternas_and_one_leftover():
    hand = cards("7o 7c 7e 7b  1o 2o 3o  11c 11e 11b  12o")
    result = CLASSIC.validar_cierre(hand)
    assert result.es_valida, result.causa


def test_classic_valid_with_runs():
    hand = cards("1c 2c 3c 4c  5e 6e 7e  10b 11b 12b  2o")
    assert CLASSIC.validar_cierre(hand).es_valida


def test_classic_three_ternas_without_cuarta_is_invalid():
    hand = cards("7o 7c 7e  1o 2o 3o  11c 11e 11b  12o 4b")
    result = CLASSIC.validar_cierre(hand)
    assert not result.es_valida
    assert "cuarta" in result.causa


def test_classic_incomplete_ternas_is_invalid():
    hand = cards("7o 7c 7e 7b  1o 2o  11c 11e  12o 4b 5c")
    assert not CLASSIC.validar_cierre(hand).es_valida


# ----------------------------------------------------------------- Apuntado
def test_apuntado_three_ternas_and_leftovers_below_five_is_valid():
    hand = cards("7o 7c 7e  1o 2o 3o  11c 11e 11b  1b 3c")  # sobrantes = 4
    result = APUNTADO.validar_cierre(hand)
    assert result.es_valida, result.causa
    assert result.puntos_sobrantes == 4


def test_apuntado_leftovers_exactly_five_is_invalid():
    hand = cards("7o 7c 7e  1o 2o 3o  11c 11e 11b  2b 3c")  # sobrantes = 5
    result = APUNTADO.validar_cierre(hand)
    assert not result.es_valida
    assert result.puntos_sobrantes == 5
    assert "menos de 5" in result.causa


def test_apuntado_leftovers_six_is_invalid():
    hand = cards("7o 7c 7e  1o 2o 3o  11c 11e 11b  2b 4c")
    assert not APUNTADO.validar_cierre(hand).es_valida


def test_apuntado_only_two_ternas_is_invalid():
    hand = cards("7o 7c 7e  1o 2o 3o  11c 11e  5b 1b 2c")
    result = APUNTADO.validar_cierre(hand)
    assert not result.es_valida
    assert "3 ternas" in result.causa


def test_apuntado_accepts_cuarta_as_one_of_the_combinations():
    hand = cards("7o 7c 7e 7b  1o 2o 3o  11c 11e 11b  1c")
    assert APUNTADO.validar_cierre(hand).es_valida


def test_apuntado_penalty_uses_best_organisation():
    hand = cards("7o 7c 7e  12o 12c  1b 2c 3e 4o 5b 6c")
    # 7s forman terna; sobrantes: 10+10+1+2+3+4+5+6 = 41
    assert APUNTADO.calcular_penalizacion(hand) == 41


# ----------------------------------------------------------------- Fin de partida
def test_clasica_el_primer_cierre_gana():
    victoria = CLASSIC.es_fin_de_partida({"p1": 0, "p2": 0}, "p1")
    assert victoria.ganadores == ["p1"] and victoria.perdedores == ["p2"]


def test_apuntado_101_exacto_pierde_y_100_no():
    assert APUNTADO.es_fin_de_partida({"p1": 0, "p2": 100}, "p1") is None
    victoria = APUNTADO.es_fin_de_partida({"p1": 0, "p2": 101, "p3": 40}, "p1")
    assert victoria.perdedores == ["p2"] and victoria.ganadores == ["p1"]


# ----------------------------------------------------------------- Registro
def test_registry_registra_ambas_modalidades_al_iniciar():
    assert {r.mode_id for r in build_registry().modalidades()} == {"CLASICA", "APUNTADO"}


def test_registry_rechaza_modalidad_duplicada():
    registry = GameModeRegistry().registrar(ReglaClasicaStrategy())
    with pytest.raises(ValueError):
        registry.registrar(ReglaClasicaStrategy())
