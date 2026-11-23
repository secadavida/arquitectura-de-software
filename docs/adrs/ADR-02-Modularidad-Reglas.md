# ADR-02: Estrategia de Modularidad para Variabilidad de Reglas

**Título:** Encapsular la variabilidad de reglas de victoria con el patrón Strategy dentro de un monolito modular.
**Estado:** Aceptado (E1; ratificado en E2 por ADR-03 y en el MVP).

## Contexto
Ambas modalidades comparten el ciclo robar → jugar → descartar → cerrar, pero difieren en la condición
de victoria y en las penalizaciones. Alternativas evaluadas:

1. Condicionales `if modalidad == CLASICA` dentro de `TurnOrchestratorComponent`.
2. Strategy en un monolito modular: interfaz `ReglaJuego` con implementaciones intercambiables.
3. Microkernel / Plug-in: cada modalidad como plugin cargable en tiempo de ejecución.

## Decisión
Se adopta la alternativa (2). `ReglaJuego` define `validarCierre(mano)`, `calcularPenalizacion(mano)` y
`esFinDePartida(jugadores)`; las estrategias se seleccionan al crear la partida según la modalidad.
Justificación: Extensibility (nueva modalidad = nueva clase), Testability (cada regla se prueba aislada),
KISS/YAGNI (el microkernel agrega carga dinámica innecesaria para el MVP) y DRY (el ciclo de turno se
escribe una sola vez).

## Consecuencias
- (+) Núcleo estable; agregar reglas futuras es una nueva implementación; pruebas aisladas.
- (−) Una indirección adicional en tiempo de ejecución; hay que definir bien el contrato de
  `ResultadoValidacion`. Deuda diferida: migrar a Microkernel si las variantes crecen mucho.

## Cumplimiento
- **Automatizado:** el build falla si `TurnOrchestratorComponent` referencia una estrategia concreta
  (`.importlinter` contrato 2).
- **Automatizado:** casos borde de sobrantes = 4, 5 y 6 pts (`tests/unit/test_reglas.py`).
- **Manual:** cada modalidad nueva se agrega como clase nueva, no como un `if` adicional.

## Evidencia en el MVP (Entregable 3)
| Nombre en E1/E2 | Código |
|---|---|
| `ReglaJuego` / `IRuleEvaluator` | `app/core/rule_engine/interfaces.py::IRuleEvaluator` |
| `validarCierre(mano)` | `validar_cierre(mano) -> ResultadoValidacion` |
| `calcularPenalizacion(mano)` | `calcular_penalizacion(mano) -> int` |
| `esFinDePartida(jugadores)` | `es_fin_de_partida(acumulados, cerrador) -> VictoryResult \| None` |
| `ResultadoValidacion` | `ResultadoValidacion(es_valida, causa, puntos_sobrantes)` |
| `ReglaClasicaCuartaTerna` / `ReglaClasicaStrategy` | `app/core/rule_engine/regla_clasica.py` |
| `ReglaApuntado101` / `ReglaApuntadoStrategy` | `app/core/rule_engine/regla_apuntado.py` |

Se añadió `sugerir(mano)` al contrato para resaltar combinaciones en la interfaz (ayuda de usabilidad).
