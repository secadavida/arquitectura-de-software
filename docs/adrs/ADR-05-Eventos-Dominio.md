# ADR-05: Estrategia de sincronización y comunicación entre componentes

**Título:** Sincronización bidireccional mediante WebSockets, control de concurrencia en memoria y
persistencia diferida vía Outbox.
**Estado:** Aceptado (E2).

## Contexto
Las salas multijugador deben difundir en tiempo real los cambios (robos, descartes, expiración del
temporizador). Riesgos: condiciones de carrera (dos cierres simultáneos, robo del pozo) y saturación de
la base relacional si cada descarte se escribe directamente.

## Decisión
1. **WebSockets full-duplex:** `SessionNotificationComponent` (WebSocket Gateway) difunde eventos
   (`TurnStarted`, `CardPlayed`, `RoundClosed`, `ScoreUpdated`...).
2. **Cerrojo en memoria `SET NX`:** ante cualquier acción se toma un bloqueo en Redis; solo la primera
   solicitud se valida; las concurrentes se rechazan para reintento.
3. **Outbox:** durante la ronda las jugadas viven en Redis; al cerrar la ronda o la sesión se vuelcan a
   PostgreSQL en una única transacción ACID; si falla, *rollback*.

## Consecuencias
- (+) Respuesta inmediata; integridad atómica (sin cierres duplicados); base relacional desacoplada.
- (−) Si Redis cae durante una ronda se puede perder el progreso volátil (mitigado con snapshot, R4);
  el cliente necesita reconexión automática.

## Cumplimiento
- Contrato 3 (capas): `app.api → app.core.orchestrator → app.core.game_session → app.core.rule_engine →
  app.core.deck_card`. Contrato 6: la capa de entrada no toca `app.infrastructure`, `redis` ni `sqlalchemy`.
- Pruebas de concurrencia: `test_accion_concurrente_se_rechaza_mientras_hay_cerrojo`,
  `test_redis_set_nx_da_exclusion_mutua`, `test_segundo_cierre_de_la_misma_ronda_se_rechaza`.

## Evidencia en el MVP (Entregable 3)
| Elemento | Código |
|---|---|
| WebSocket Gateway `/ws/games/{id}` | `app/api/websockets.py` |
| `SET NX PX` + liberación segura | `RedisGameStateStore.lock()` |
| Versión del estado en cada jugada (R2) | `GameState.version`; `StaleStateError` → HTTP 409 con `current_version` |
| Outbox `game:{id}:plays` | `append_play` / `pending_plays` / `clear_plays` |
| Volcado ACID + `SELECT … FOR UPDATE` (R1, R6) | `PostgresHistoryStore.settle_round()` |
| Temporizador y acción por defecto (R8, RF10) | `TurnOrchestratorComponent.expirar_turnos()` + tarea en `app/api/__init__.py` |

**Diferencias con el E2:**
- Los mensajes WebSocket solo llevan el tipo de evento y la versión. Cada cliente vuelve a pedir su
  propia vista, para nunca difundir manos ajenas.
- No se envía `TimerTick`: el cliente calcula la cuenta regresiva a partir de `turn_remaining`.
- La ventana de gracia por desconexión (R5) no se implementó. Al reconectar, el cliente recibe el
  estado completo.
