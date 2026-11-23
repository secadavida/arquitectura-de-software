# Juego de Cartas Apuntado — Versión Digital (MVP)

[![CI - Fitness Functions](https://github.com/secadavida/arquitectura-de-software/actions/workflows/ci.yml/badge.svg)](https://github.com/secadavida/arquitectura-de-software/actions/workflows/ci.yml)

**Fundamentos de Arquitectura de Software** — Universidad Nacional de Colombia, sede Medellín.
Marco teórico: Richards & Ford, *Fundamentals of Software Architecture* (2.ª ed., 2025).

**Equipo:** Sebastián Cadavid Ahumada · Daniel Felipe Garzón Acosta · Andrés Felipe Rojas Gutiérrez · David Agudelo Arboleda

Este repositorio implementa el MVP del **Entregable 3** siguiendo las decisiones del E1 (ADR-01, ADR-02)
y del E2 (ADR-03 a ADR-05): **monolito modular con patrón Strategy**, `GameModeRegistry`, persistencia
políglota **Redis + PostgreSQL (3FN)**, WebSockets, cerrojo `SET NX`, patrón **Outbox** y gobernanza con
**import-linter + pytest + radon + ruff**.

---

## Ficha técnica

| | |
|---|---|
| **Estilo** | Monolito modular, particionado por dominio, con Strategy para las reglas (ADR-01, 02, 03) |
| **Backend** | Python 3.12 · FastAPI · Uvicorn (ASGI) |
| **Frontend** | HTML + CSS + JavaScript sin framework, servido por FastAPI |
| **Tiempo real** | WebSocket Gateway `/ws/games/{id}` (ADR-05) |
| **Persistencia** | Redis 7 (estado vivo, Outbox, cerrojo) + PostgreSQL 16 en 3FN (historial, snapshots) (ADR-04) |
| **Concurrencia** | `SET NX PX` por partida + versión del estado en cada jugada (R2) + `SELECT … FOR UPDATE` al liquidar (R6) |
| **Gobernanza** | `.importlinter` (6 contratos), `ruff` C901, `pytest tests/architecture`, GitHub Actions |
| **Despliegue** | `docker compose` (app + redis + postgres) |
| **Multijugador** | 2-4 jugadores en red local, cada uno en su dispositivo, o en varias pestañas de un mismo equipo |

### Modalidades
- **Clásica (4-3-3):** con 11 cartas en mano, en tu turno robas (quedas con 12) y cierras descartando
  una carta. Las 11 restantes deben formar **1 cuarta + 2 ternas + 1 sobrante**. Gana el primero que cierre.
- **Apuntado (101):** cierras con **3 ternas** (una puede ser cuarta) y sobrantes que sumen **menos de
  5 pts** (exactamente 5 no vale). Los demás suman sus sobrantes; quien llegue a **101 o más** pierde.

Una combinación es un grupo (mismo número, palos distintos) o una escalera (mismo palo, consecutivas en
1-7, Sota, Caballo, Rey). Las figuras valen 10 pts. Con 4 jugadores se usan 2 barajas. Hay temporizador
por turno, configurable (60 s por defecto; 0 = sin límite).

---

## Ejecución

### Opción A — Docker (recomendada; topología completa del ADR-04)
```bash
docker compose up --build
```
Abrir <http://127.0.0.1:8000>. Desde otros dispositivos de la misma red: `http://<IP-del-equipo>:8000`.

### Opción B — Python local (modo desarrollo, sin Docker)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Sin `REDIS_URL` ni `DATABASE_URL` la app usa un almacén en memoria y SQLite (`data/apuntado-dev.db`),
y lo advierte en el log. Para usar Redis y PostgreSQL locales, define las variables:

| Variable | Ejemplo |
|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` |
| `DATABASE_URL` | `postgresql+psycopg2://apuntado:apuntado@localhost:5432/apuntado` |
| `LOG_LEVEL` | `INFO` |

### Cómo jugar
1. En la página principal elige la modalidad, escribe 2-4 nombres y el tiempo por turno, y pulsa **Crear partida**. El sistema muestra el **PIN** de la sala.
2. Cada jugador abre su enlace o entra con el PIN en **Unirse con PIN**.
3. En tu turno: pulsa **Mazo** o **Pozo** para robar, selecciona una carta y elige **Descartar** o **Cerrar ronda descartando la seleccionada**.
4. Las cartas con el mismo color de fondo forman una combinación sugerida. El registro de auditoría está al final de la página.

---

## Arquitectura
```
app/
├── core/                    # game_engine (ADR-01): no depende de FastAPI, Redis ni SQLAlchemy
│   ├── deck_card/           # Deck & Card — DeckManagementComponent
│   ├── rule_engine/         # Rule Engine — HandEvaluator, IRuleEvaluator, ReglaClasicaStrategy,
│   │                        #   ReglaApuntadoStrategy, RoundScoring, GameModeRegistry
│   ├── game_session/        # Game Session — GameState, GameSessionComponent (mediador), puertos
│   └── orchestrator/        # Turn & Timer — TurnOrchestratorComponent (mediador de turnos)
├── infrastructure/
│   ├── models/              # Esquema 3FN (SQLAlchemy)
│   └── persistence/         # RedisGameStateStore, PostgresHistoryStore, InMemoryGameStateStore
├── api/                     # REST + WebSocket Gateway + cliente web (static/)
├── bootstrap.py             # composition root: registra las modalidades y conecta Redis/PostgreSQL
└── main.py                  # punto de entrada ASGI
```
Capas (contrato 3): `api → orchestrator → game_session → rule_engine → deck_card`.

## Fitness functions y pruebas
```bash
lint-imports                       # 6 contratos de .importlinter
ruff check app --select C901       # complejidad ciclomática <= 10
pytest -v                          # 63 pruebas: unitarias, integración y arquitectura
python -m scripts.metrics_report reports/metricas.md   # CC, Ca/Ce/I/A/D, MI
```

| Exigencia del E3 | Cómo se verifica |
|---|---|
| Prueba 1: reglas sin acoplamiento cruzado | Contrato 1 (aislamiento del Rule Engine), 2 (el orquestador solo usa `IRuleEvaluator`) y 4 (estrategias independientes) |
| Prueba 2: UI aislada del almacenamiento | Contrato 5 (núcleo sin infraestructura) y 6 (`app.api` no importa `app.infrastructure`, `redis` ni `sqlalchemy`) |
| Prueba 3: sin dependencias cíclicas | Contrato 3 (capas) + `test_sin_dependencias_ciclicas_entre_modulos` (grafo AST completo) |
| Complejidad ciclomática | `ruff C901` + radon en `tests/architecture` (CC máx. actual: 8) |
| Secuencia principal | D ≤ 0.5 para cada estrategia de reglas |

El workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) tiene cuatro jobs:
- fitness functions;
- pruebas unitarias;
- integración contra **Redis 7 y PostgreSQL 16 reales**;
- build y smoke test con `docker compose`.

## Documentación (`/docs`)
| Sección del informe E3 | Archivo |
|---|---|
| 1.1 Despliegue | [docs/diagrams/e3_1_despliegue.puml](docs/diagrams/e3_1_despliegue.puml) |
| 1.2 Secuencia de cierre y liquidación | [docs/diagrams/e3_2_secuencia_cierre.puml](docs/diagrams/e3_2_secuencia_cierre.puml) |
| 1.3 Clases de implementación | [docs/diagrams/e3_3_clases_implementacion.puml](docs/diagrams/e3_3_clases_implementacion.puml) |
| Modelo relacional implementado | [docs/diagrams/classes_persistencia.puml](docs/diagrams/classes_persistencia.puml) |
| 2.3 Checklists | [docs/checklists.md](docs/checklists.md) |
| 3 Validación con usuarios | [docs/validacion/protocolo.md](docs/validacion/protocolo.md) |
| 4.2 Métricas | [docs/metricas/reporte_metricas.md](docs/metricas/reporte_metricas.md) |
| 5 ADRs y retrospectiva | [docs/adrs/](docs/adrs/README.md) |

Los `.puml` se pueden ver con la extensión PlantUML de VS Code o en <https://www.plantuml.com/plantuml>.

Métricas de las sesiones con usuarios (con la app corriendo):
```bash
python -m scripts.session_report --url http://127.0.0.1:8000 --csv docs/validacion/evidencias/logs/metricas_sistema.csv
```
