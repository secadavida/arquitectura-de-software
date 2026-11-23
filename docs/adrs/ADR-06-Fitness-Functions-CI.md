# ADR-06: Gobernanza con fitness functions en GitHub Actions

**Estado:** Aceptado (Entregable 3). Implementa la sección 5 del E2.

## Contexto
Un monolito modular se erosiona con facilidad (*architectural drift*). El E2 definió tres reglas: aislamiento
de capas, independencia de reglas sin ciclos y CC ≤ 10, verificadas con `import-linter`, `pytest`, `radon`
y `ruff`.

## Decisión
Workflow `.github/workflows/ci.yml` con cuatro jobs:

1. **Fitness functions:** `lint-imports` (6 contratos), `ruff --select C901`,
   `pytest tests/architecture` (contratos + CC con Radon + ciclos sobre el grafo AST + distancia a la
   secuencia principal de cada estrategia). Publica el reporte de métricas en el resumen del job.
2. **Pruebas unitarias** (`tests/unit`).
3. **Integración** contra Redis 7 y PostgreSQL 16 como *service containers*.
4. **docker compose** build + smoke test (solo si los anteriores pasan).

| Prueba exigida por el E3 | Contrato / prueba |
|---|---|
| Prueba 1: aislamiento de módulos de reglas | Contratos 1, 2 y 4 |
| Prueba 2: UI aislada del almacenamiento | Contratos 5 y 6 |
| Prueba 3: sin dependencias cíclicas | Contrato 3 (capas) + `test_sin_dependencias_ciclicas_entre_modulos` |

## Consecuencias
- (+) Una violación rompe el build. Se verificó inyectando violaciones a propósito (el orquestador
  importando `regla_clasica`, la API importando `redis_repo`, un ciclo `deck_card → rule_engine` y un
  acoplamiento entre estrategias): fallaron los contratos 2, 3, 4 y 6 y la prueba de ciclos, y todo volvió
  a verde al revertir.
- (−) Las reglas analizan imports estáticos. El *composition root* (`app/bootstrap.py`) queda fuera de
  los contratos por diseño, porque es el único que debe conocer todas las piezas.
