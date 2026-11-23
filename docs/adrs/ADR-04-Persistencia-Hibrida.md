# ADR-04: Selección del motor y modelo de persistencia (SQL vs NoSQL)

**Título:** Persistencia políglota: Redis en memoria para salas interactivas y PostgreSQL en 3FN para la
consolidación histórica.
**Estado:** Aceptado (E2).

## Contexto
Las salas en tiempo real generan dos tipos de datos con necesidades opuestas:

- **Efímeros:** mazo, manos, turno, temporizador y marcadores parciales; requieren lecturas/escrituras
  de sub-milisegundos.
- **Persistentes:** perfiles, billeteras, registro inmutable de auditoría y progresión acumulada hasta 101.

Alternativas: relacional pura (cuellos de botella de I/O con muchas salas) o híbrida (Polyglot Persistence).

## Decisión
- **Redis:** estado volátil de la sesión activa (mazo, manos, turno actual, temporizador).
- **PostgreSQL (3FN):** `User`, `Wallet`, `Room`, `GameSession`, `PlayerSession`, `Round`, `Score`, `Play`.
  `GameSession` 1:N `Round` modela las sesiones acumulativas de Apuntado.

## Consecuencias
- (+) Alta capacidad de respuesta; consistencia transaccional ACID para puntajes; esquema extensible.
- (−) Dos motores que administrar; flujo riguroso de sincronización memoria → disco.

## Cumplimiento
- `rule_engine` no puede importar `redis`, `sqlalchemy` ni `app.infrastructure` (contratos 1 y 5).
- Pruebas de integración contra Redis 7 y PostgreSQL 16 reales en CI (`integration-tests`).

## Evidencia en el MVP (Entregable 3)
| Elemento | Código |
|---|---|
| Estado vivo `game:{id}:state` | `app/infrastructure/persistence/redis_repo.py` |
| Esquema 3FN | `app/infrastructure/models/` (`users`, `wallets`, `rooms`, `game_sessions`, `player_sessions`, `rounds`, `scores`, `plays`) |
| Repositorio relacional | `app/infrastructure/persistence/postgres_repo.py` |
| Snapshot por ronda (mitigación R4) | tabla `game_snapshots` + `GameSessionComponent.cargar()` |
| Topología | `docker-compose.yml` (app + redis:7 + postgres:16) |

**Ajustes al modelo del E2** (diagrama `docs/diagrams/classes_persistencia.puml`):
`player_sessions.seat` (asiento p1..p4), `plays.payload` (detalle JSON, p. ej. causa de cierre inválido),
`rounds.status` OPEN/CLOSED y la tabla `game_snapshots`. `wallets` existe pero Economy no se implementó
(ADR-07). En desarrollo sin Docker, la app usa un almacén en memoria y SQLite (`app/bootstrap.py`); en
Docker y CI se usan Redis y PostgreSQL.
