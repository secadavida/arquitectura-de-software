# Reporte de métricas estructurales — Apuntado Digital (MVP)

## Complejidad ciclomática (Radon)

- Bloques analizados: **218**
- CC promedio: **1.91**
- CC máxima: **8** (umbral de la fitness function: 10; deseable < 5)
- Bloques con CC >= 5: **10**

### Métodos de evaluación de ternas/cuartas y liquidación

| Archivo | Bloque | CC | Rango |
|---|---|---:|:---:|
| `core/rule_engine/hand_evaluator.py` | `is_group` | 4 | A |
| `core/rule_engine/hand_evaluator.py` | `is_run` | 4 | A |
| `core/rule_engine/hand_evaluator.py` | `classify` | 4 | A |
| `core/rule_engine/hand_evaluator.py` | `candidate_melds` | 6 | B |
| `core/rule_engine/hand_evaluator.py` | `_remove_size` | 1 | A |
| `core/rule_engine/hand_evaluator.py` | `_disjoint_selections` | 6 | B |
| `core/rule_engine/hand_evaluator.py` | `best_arrangement` | 6 | B |
| `core/rule_engine/hand_evaluator.py` | `best_of_plans` | 4 | A |
| `core/rule_engine/hand_evaluator.py` | `best_partial` | 2 | A |
| `core/rule_engine/hand_evaluator.py` | `MeldKind` | 1 | A |
| `core/rule_engine/hand_evaluator.py` | `Meld` | 2 | A |
| `core/rule_engine/hand_evaluator.py` | `Meld.size` | 1 | A |
| `core/rule_engine/hand_evaluator.py` | `Arrangement` | 2 | A |
| `core/rule_engine/hand_evaluator.py` | `Arrangement.leftover_points` | 1 | A |
| `core/rule_engine/regla_apuntado.py` | `ReglaApuntadoStrategy` | 4 | A |
| `core/rule_engine/regla_apuntado.py` | `ReglaApuntadoStrategy.validar_cierre` | 3 | A |
| `core/rule_engine/regla_apuntado.py` | `ReglaApuntadoStrategy.calcular_penalizacion` | 1 | A |
| `core/rule_engine/regla_apuntado.py` | `ReglaApuntadoStrategy.es_fin_de_partida` | 8 | B |
| `core/rule_engine/regla_apuntado.py` | `ReglaApuntadoStrategy.sugerir` | 2 | A |
| `core/rule_engine/regla_clasica.py` | `ReglaClasicaStrategy` | 3 | A |
| `core/rule_engine/regla_clasica.py` | `ReglaClasicaStrategy.validar_cierre` | 2 | A |
| `core/rule_engine/regla_clasica.py` | `ReglaClasicaStrategy.calcular_penalizacion` | 1 | A |
| `core/rule_engine/regla_clasica.py` | `ReglaClasicaStrategy.es_fin_de_partida` | 3 | A |
| `core/rule_engine/regla_clasica.py` | `ReglaClasicaStrategy.sugerir` | 2 | A |
| `core/rule_engine/round_scoring.py` | `ResultadoRonda` | 2 | A |
| `core/rule_engine/round_scoring.py` | `ResultadoRonda.fin_de_partida` | 1 | A |
| `core/rule_engine/round_scoring.py` | `RoundScoring` | 6 | B |
| `core/rule_engine/round_scoring.py` | `RoundScoring.liquidar` | 5 | A |

## Acoplamiento y distancia a la secuencia principal

Ca = aferente, Ce = eferente, I = Ce/(Ca+Ce), A = abstractas/total, D = |A+I-1|.
Se excluyen el composition root (`app.bootstrap`, `app.main`) y `app.core.errors`.

| Componente | Ca | Ce | I | A | D | Zona |
|---|---:|---:|---:|---:|---:|---|
| `app.api` | 0 | 1 | 1.00 | 0.00 | 0.00 | secuencia principal |
| `app.core.deck_card` | 4 | 0 | 0.00 | 0.00 | 1.00 | zona de dolor |
| `app.core.game_session` | 1 | 2 | 0.67 | 0.27 | 0.06 | secuencia principal |
| `app.core.orchestrator` | 1 | 1 | 0.50 | 0.00 | 0.50 | secuencia principal |
| `app.core.rule_engine` | 3 | 1 | 0.25 | 0.11 | 0.64 | zona de dolor |
| `app.core.rule_engine.regla_apuntado` | 0 | 2 | 1.00 | 0.00 | 0.00 | secuencia principal |
| `app.core.rule_engine.regla_clasica` | 0 | 2 | 1.00 | 0.00 | 0.00 | secuencia principal |
| `app.infrastructure` | 0 | 0 | 0.00 | 0.00 | 1.00 | aislado (solo lo conecta el composition root) |

Dependencias cíclicas detectadas: **0**

## Índice de mantenibilidad (Radon MI)

| Módulo | MI |
|---|---:|
| `app/__init__.py` | 100.0 |
| `app/api/__init__.py` | 100.0 |
| `app/api/http.py` | 68.5 |
| `app/api/websockets.py` | 72.7 |
| `app/bootstrap.py` | 100.0 |
| `app/core/__init__.py` | 100.0 |
| `app/core/deck_card/__init__.py` | 100.0 |
| `app/core/deck_card/cards.py` | 67.1 |
| `app/core/deck_card/deck.py` | 57.2 |
| `app/core/errors.py` | 100.0 |
| `app/core/game_session/__init__.py` | 100.0 |
| `app/core/game_session/ports.py` | 100.0 |
| `app/core/game_session/session.py` | 51.2 |
| `app/core/game_session/snapshot.py` | 100.0 |
| `app/core/game_session/state.py` | 40.2 |
| `app/core/game_session/views.py` | 64.6 |
| `app/core/orchestrator/__init__.py` | 100.0 |
| `app/core/orchestrator/turn_orchestrator.py` | 62.1 |
| `app/core/rule_engine/__init__.py` | 100.0 |
| `app/core/rule_engine/hand_evaluator.py` | 54.7 |
| `app/core/rule_engine/interfaces.py` | 79.5 |
| `app/core/rule_engine/registry.py` | 89.1 |
| `app/core/rule_engine/regla_apuntado.py` | 69.3 |
| `app/core/rule_engine/regla_clasica.py` | 80.7 |
| `app/core/rule_engine/round_scoring.py` | 77.9 |
| `app/infrastructure/__init__.py` | 100.0 |
| `app/infrastructure/models/__init__.py` | 100.0 |
| `app/infrastructure/models/base.py` | 100.0 |
| `app/infrastructure/models/game_session.py` | 100.0 |
| `app/infrastructure/models/user.py` | 100.0 |
| `app/infrastructure/persistence/__init__.py` | 100.0 |
| `app/infrastructure/persistence/memory_repo.py` | 70.5 |
| `app/infrastructure/persistence/postgres_repo.py` | 47.2 |
| `app/infrastructure/persistence/redis_repo.py` | 64.1 |
| `app/main.py` | 100.0 |
