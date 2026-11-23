# ADR-03: Estilo arquitectónico y mecanismo de extensibilidad de reglas

**Título:** Selección de Monolito Modular con patrón Strategy y Registro desacoplado para soportar salas
interactivas y extensibilidad de modalidades.
**Estado:** Aceptado (E2).

## Contexto
El sistema opera con salas interactivas donde varios usuarios participan a la vez y requieren
sincronización en tiempo real de turnos y temporizadores. El motor debe procesar dos modalidades:

1. **Regla Clásica:** mano cerrada 4-3-3 (una cuarta, dos ternas y un descarte) resuelta en una única
   ronda, sin acumulación de penalizaciones.
2. **Regla Apuntado:** sesión multironda limitada por un umbral acumulativo (≥ 101 puntos) y cierre
   con tres ternas y sobrante menor a 5 puntos.

La arquitectura debe ser extensible para futuras modalidades (Continental, Póker, variaciones por tiempo
o con comodines) sin alterar el orquestador. Se evaluaron Microkernel (plug-ins dinámicos) y Monolito
Modular con Strategy y Registry interno (matriz ponderada del E2: Monolito Modular 53, Microkernel 50,
Service-Based 37).

## Decisión
Monolito Modular en un único quantum de despliegue, con Strategy y un catálogo `GameModeRegistry` en
`game_engine.rule_engine`:

1. **Aislamiento del orquestador:** `TurnOrchestratorComponent` solo usa la interfaz `IRuleEvaluator`, sin
   `if/else` por modalidad.
2. **Modalidades base:** `ReglaClasicaStrategy` y `ReglaApuntadoStrategy` encapsulan validación, cierre y
   puntuación.
3. **Extensión futura:** una variante nueva es una clase que implementa `IRuleEvaluator` y se agrega al
   registro.

## Consecuencias
- (+) Extensibilidad aislada (Open/Closed); baja latencia (validación en memoria, p95 < 500 ms);
  testabilidad focalizada.
- (−) El registro se llena al iniciar el servidor: una modalidad nueva exige redesplegar (sin carga en
  caliente). Exige controles para que la lógica no se acople a infraestructura ni a la capa de entrada.

## Cumplimiento
- `lint-imports` en CI. Contrato 2: `app.core.orchestrator` (y `app.core.game_session`) no pueden
  importar `app.core.rule_engine.regla_clasica` ni `regla_apuntado`.

## Evidencia en el MVP (Entregable 3)
- `app/core/rule_engine/registry.py::GameModeRegistry` (sin `importlib`, sin carga dinámica).
- Registro al iniciar: `app/bootstrap.py::build_registry()`, el *composition root* es el único módulo
  que importa las estrategias concretas.
- **Corrección respecto al E2:** el contrato 2 publicado en el E2 apuntaba a `app.core.rules.*`, ruta que
  no existe; en el MVP se corrigió a `app.core.rule_engine.regla_*`.
