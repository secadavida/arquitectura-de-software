# ADR-07: Alcance del MVP y módulos diferidos

**Estado:** Aceptado (Entregable 3).

## Contexto
El E1/E2 definen 10 módulos (Identity, Social, Lobby & Room, Game Session, Rule Engine, Turn & Timer,
Deck & Card, Economy, Audit & History, Notification). El alcance del MVP exigido por el E3 es: motor de
juego con ambas modalidades, gestión en tiempo real del mazo, pozo, manos y turnos, validación con
usuarios y gobernanza en CI.

## Decisión
| Módulo | En el MVP |
|---|---|
| Deck & Card, Rule Engine, Game Session, Turn & Timer | Completo |
| Notification (WebSocket) | Completo |
| Audit & History | Registro de jugadas (`plays`) + snapshots; consulta vía `/api/games/{id}/events` |
| Lobby & Room | Mínimo: crear sala con PIN, cupo 2-4 y tiempo por turno; unirse por PIN. Sin expulsión (CU03) |
| Identity & Profile | Diferido: los jugadores son usuarios invitados (`users.is_guest`) |
| Social, Economy (apuestas, billetera) | Diferidos: las tablas `wallets` existen pero no se usan |

## Consecuencias
- (+) El esfuerzo se concentra en los drivers D1 (extensibilidad), D5 (testabilidad) y D4 (responsiveness).
- (−) Sin autenticación, un jugador se identifica por su enlace (`?player=p1`): RNF07 (Seguridad) queda
  pendiente. Sin Economy, la liquidación ACID (R1) cubre puntajes pero no monedas.
