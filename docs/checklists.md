# Checklists de ingeniería (Richards & Ford, cap. 24)

Marquen cada casilla **cuando ustedes la hayan verificado** antes de la entrega y anoten la evidencia.
Las casillas que ya aparecen marcadas se verificaron al construir el MVP.

## 1. Developer Code-Completion Checklist

| # | Ítem | Estado | Evidencia |
|---|---|:---:|---|
| 1 | Sin `print()` ni `console.log` de depuración en `app/` | [x] | `grep -rnE "print\(\|console\.log" app/` sin resultados |
| 2 | Sin excepciones absorbidas en silencio | [x] | Los `except` de `app/` registran el error en el log (`realtime`, temporizador) o lo traducen a HTTP |
| 3 | Errores de dominio traducidos a HTTP: 409 regla/versión, 423 cerrojo, 404, 400 | [x] | `app/api/__init__.py` |
| 4 | `ruff check` sin errores y CC ≤ 10 (C901) | [x] | Job *fitness-functions* |
| 5 | Sin código comentado ni TODOs pendientes | [ ] | Revisar antes de entregar |
| 6 | Sin secretos en el repositorio | [x] | Credenciales solo de desarrollo en `docker-compose.yml`; `.env` ignorado |

## 2. Unit & Functional Testing Checklist

| # | Caso | Prueba |
|---|---|---|
| 1 | Clásica: 1 cuarta + 2 ternas + 1 sobrante → válido | `test_reglas.py::test_classic_valid_cuarta_two_ternas_and_one_leftover` |
| 2 | Clásica con escaleras → válido | `test_classic_valid_with_runs` |
| 3 | Clásica con 3 ternas sin cuarta → inválido | `test_classic_three_ternas_without_cuarta_is_invalid` |
| 4 | Ternas incompletas → inválido | `test_classic_incomplete_ternas_is_invalid`, `test_apuntado_only_two_ternas_is_invalid` |
| 5 | Apuntado: sobrantes = 4 → válido | `test_apuntado_three_ternas_and_leftovers_below_five_is_valid` |
| 6 | **Apuntado: sobrantes exactamente 5 → inválido** | `test_apuntado_leftovers_exactly_five_is_invalid` |
| 7 | Apuntado: sobrantes = 6 → inválido | `test_apuntado_leftovers_six_is_invalid` |
| 8 | **Detección exacta de 101** (95 + 6 = 101 pierde; 100 no) | `test_turn_orchestrator.py::test_apuntado_llegar_exactamente_a_101_termina_la_partida`, `test_apuntado_100_puntos_no_termina` |
| 9 | Penalización con la mejor organización | `test_apuntado_penalty_uses_best_organisation` |
| 10 | Turnos: fuera de turno → 409 | `test_no_se_puede_jugar_fuera_de_turno`, `test_fuera_de_turno_devuelve_409` |
| 11 | Cierre inválido conserva mano y turno, y queda auditado | `test_cierre_invalido_conserva_turno_mano_y_queda_auditado` |
| 12 | R2: versión desactualizada → 409 | `test_jugada_con_version_desactualizada_se_rechaza` |
| 13 | ADR-05: cerrojo SET NX | `test_accion_concurrente_se_rechaza_mientras_hay_cerrojo`, `test_redis_set_nx_da_exclusion_mutua` |
| 14 | R1: rollback de la liquidación | `test_fallo_en_la_transaccion_hace_rollback` |
| 15 | R6: doble cierre de la misma ronda | `test_segundo_cierre_de_la_misma_ronda_se_rechaza`, `test_liquidacion_es_atomica_y_rechaza_doble_cierre` |
| 16 | R4: reanudación desde snapshot | `test_reanuda_desde_snapshot_si_se_pierde_redis` |
| 17 | R8: temporizador y acción por defecto | `test_turno_vencido_aplica_accion_por_defecto` |
| 18 | Flujo HTTP, PIN y WebSocket | `tests/integration/test_api.py` |

Ejecutar: `pytest -v` (63 pruebas). En CI, `tests/integration` corre contra Redis y PostgreSQL reales.

## 3. Software Release Checklist

| # | Ítem | Estado | Evidencia |
|---|---|:---:|---|
| 1 | Esquema de BD creado al iniciar (`metadata.create_all`, idempotente) | [x] | `create_db_engine()` |
| 2 | Variables de entorno documentadas (`REDIS_URL`, `DATABASE_URL`, `LOG_LEVEL`, `PORT`) | [x] | README, `docker-compose.yml` |
| 3 | Build en verde en GitHub Actions (4 jobs) | [ ] | Captura de la pestaña *Actions* |
| 4 | `docker compose up --build` levanta app + Redis + PostgreSQL y `/health` responde | [ ] | Captura |
| 5 | Versión etiquetada (`git tag v1.0.0`) | [ ] | |
| 6 | Evidencias de validación con usuarios en `docs/validacion/` | [ ] | |
