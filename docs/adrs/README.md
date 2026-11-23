# Registro de decisiones arquitectónicas

| ADR | Decisión | Origen | Estado |
|---|---|---|---|
| [ADR-01](ADR-01-Particionamiento.md) | Particionamiento por dominio | E1 | Aceptado |
| [ADR-02](ADR-02-Modularidad-Reglas.md) | Strategy para la variabilidad de reglas | E1 | Aceptado |
| [ADR-03](ADR-03-Estilo-Arquitectonico.md) | Monolito modular + Strategy + GameModeRegistry | E2 | Aceptado |
| [ADR-04](ADR-04-Persistencia-Hibrida.md) | Persistencia políglota Redis + PostgreSQL 3FN | E2 | Aceptado |
| [ADR-05](ADR-05-Eventos-Dominio.md) | WebSockets, SET NX y Outbox | E2 | Aceptado |
| [ADR-06](ADR-06-Fitness-Functions-CI.md) | Fitness functions en GitHub Actions | E3 | Aceptado |
| [ADR-07](ADR-07-Alcance-MVP.md) | Alcance del MVP y módulos diferidos | E3 | Aceptado |

Cada ADR del E1/E2 incluye una sección **"Evidencia en el MVP"** con dónde quedó implementada la
decisión y las diferencias encontradas al implementarla (insumo para la sección 5 del informe).
