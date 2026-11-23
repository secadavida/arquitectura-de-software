"""Métricas de validación con usuarios a partir del registro de jugadas (sección 3.2/3.3).

Consulta la API (no la base de datos), así funciona igual con Docker o en local:

    python -m scripts.session_report                              # partidas recientes
    python -m scripts.session_report <game_id> ...                # partidas concretas
    python -m scripts.session_report --url http://127.0.0.1:8000 --csv docs/validacion/evidencias/logs/metricas_sistema.csv

Por jugador: turnos jugados, tiempo promedio por turno (desde que el turno queda
habilitado hasta el descarte o cierre), cierres válidos/inválidos y causas de
rechazo, y turnos expirados por el temporizador. Complementa (no reemplaza) la
encuesta SUS y las notas del observador.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

TURN_RESET = {"partida_creada", "ronda_iniciada", "descarte", "turno_expirado", "partida_reanudada"}


def _get(url: str):
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def _ts(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _ends_turn(event: dict) -> bool:
    valid_close = event["event"] == "cierre_intentado" and event["data"].get("valido")
    return event["event"] == "descarte" or bool(valid_close)


def _new_stats() -> dict:
    return {"turnos": 0, "segundos": 0.0, "cierres_validos": 0, "cierres_invalidos": 0,
            "turnos_expirados": 0, "causas": []}


def _count(event: dict, stats: dict) -> None:
    entry = stats[event["player_id"]]
    if event["event"] == "turno_expirado":
        entry["turnos_expirados"] += 1
    elif event["event"] == "cierre_intentado":
        key = "cierres_validos" if event["data"].get("valido") else "cierres_invalidos"
        entry[key] += 1
        if key == "cierres_invalidos":
            entry["causas"].append(event["data"].get("causa", ""))


def analyse(game: dict, events: list[dict]) -> list[dict]:
    names = {p["id"]: p["name"] for p in game["players"]}
    stats: dict[str, dict] = defaultdict(_new_stats)
    turn_start = None
    for event in events:
        now = _ts(event["ts"])
        if event["player_id"]:
            _count(event, stats)
        if _ends_turn(event) and turn_start is not None:
            stats[event["player_id"]]["turnos"] += 1
            stats[event["player_id"]]["segundos"] += (now - turn_start).total_seconds()
        if event["event"] in TURN_RESET:
            turn_start = now
    return [_row(game, names.get(pid, pid), s) for pid, s in stats.items()]


def _row(game: dict, name: str, s: dict) -> dict:
    avg = s["segundos"] / s["turnos"] if s["turnos"] else 0.0
    return {
        "partida": game["game_id"], "pin": game["room_pin"], "modalidad": game["mode"]["id"],
        "jugador": name, "turnos": s["turnos"], "tiempo_promedio_turno_s": round(avg, 1),
        "cierres_validos": s["cierres_validos"], "cierres_invalidos": s["cierres_invalidos"],
        "turnos_expirados": s["turnos_expirados"], "causas_rechazo": " | ".join(s["causas"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("game_ids", nargs="*")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--csv", help="Ruta de salida CSV")
    args = parser.parse_args()
    ids = args.game_ids or [g["game_id"] for g in _get(f"{args.url}/api/games")]
    rows = []
    for gid in ids:
        rows += analyse(_get(f"{args.url}/api/games/{gid}"), _get(f"{args.url}/api/games/{gid}/events"))
    if args.csv and rows:
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    sys.stdout.reconfigure(encoding="utf-8")
    for r in rows:
        print(" · ".join(f"{k}={v}" for k, v in r.items()))


if __name__ == "__main__":
    main()
