# ADR-01: Selección de Tipo de Particionamiento

**Título:** Adoptar particionamiento por dominio para la arquitectura del sistema de juego de cartas.
**Estado:** Aceptado (propuesto en el Entregable 1; ratificado al implementar el MVP en el Entregable 3).

## Contexto
El sistema soporta dos modalidades (Clásica 4-3-3 y Apuntado 101) y anticipa variantes futuras
(comodines, umbral 101 configurable). Alternativas evaluadas:

- **(a) Técnico por capas** (UI, lógica, persistencia): simple al inicio, pero acopla las reglas con la
  infraestructura y cada modalidad nueva toca todas las capas.
- **(b) Por dominio:** módulos `game_engine`, `rooms`, `identity` y `persistence`, con cohesión y
  reglas desacopladas.

## Decisión
Se adopta el particionamiento por dominio como criterio primario; las capas técnicas quedan como
detalle interno de cada módulo. El driver #1 (Configurability/Extensibility) exige contener la
variabilidad de reglas dentro de `game_engine` sin propagarla al resto del sistema.

## Consecuencias
- (+) `game_engine` evoluciona aislado y se prueba sin FastAPI, Redis ni PostgreSQL; se puede trabajar
  en paralelo por módulo.
- (−) Mayor esfuerzo de diseño inicial; se requiere disciplina para no filtrar detalles técnicos entre
  módulos; la presentación debe adaptarse a los contratos de cada módulo.

## Cumplimiento
- **Automatizado:** `.importlinter` contrato 5 — `app.core` (el `game_engine`) no puede importar
  `fastapi`, `redis`, `sqlalchemy`, `psycopg2`, `app.infrastructure` ni `app.api`.
- **Manual:** revisión en cada pull request.

## Evidencia en el MVP (Entregable 3)
| Módulo del E2 | Paquete implementado |
|---|---|
| game_engine / Deck & Card | `app/core/deck_card/` |
| game_engine / Rule Engine | `app/core/rule_engine/` |
| game_engine / Game Session | `app/core/game_session/` |
| game_engine / Turn & Timer | `app/core/orchestrator/` |
| Notification | `app/api/websockets.py` |
| persistence | `app/infrastructure/` |
| Identity, Social, Economy, Lobby & Room | Fuera del alcance del MVP (ver ADR-07) |
