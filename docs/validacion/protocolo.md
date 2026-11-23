# Protocolo de validación con usuarios reales (sección 3 del informe)

> Este archivo es la **guía** para ejecutar la sesión. Los resultados se registran en
> `resultados.csv`, `encuesta_SUS.md` y la carpeta `evidencias/`. No completen datos que no hayan
> medido.

## 3.1 Diseño metodológico

**Objetivo.** Verificar que jugadores ajenos al equipo puedan completar partidas en ambas
modalidades sin asistencia, que el sistema valide correctamente los cierres y que la
retroalimentación de errores sea comprensible.

**Población.** 3 a 5 personas ajenas al equipo de desarrollo (amigos, familiares, compañeros de
otros cursos). Registrar para cada una: ID anónimo (U01…), edad aproximada, si conoce el juego
físico (sí/no), dispositivo usado.

**Entorno.**
- Servidor: `docker compose up --build` en un portátil del equipo (app + Redis + PostgreSQL); jugadores en la misma red
  Wi-Fi abriendo `http://<IP-del-portátil>:8000`, o todos en un mismo equipo con pestañas.
- Grabación de pantalla (OBS / Xbox Game Bar `Win+Alt+R`) con consentimiento verbal.
- Un observador del equipo toma notas sin intervenir.

**Consentimiento.** Explicar que se evalúa el sistema, no a la persona; pedir permiso para grabar
la pantalla (no el rostro) y usar los datos de forma anónima en el informe.

## Guion de tareas (sin asistencia técnica)

| # | Tarea | Criterio de éxito |
|---|---|---|
| T1 | Crear una partida y seleccionar la modalidad (Clásica o Apuntado) | Partida creada y enlace abierto |
| T2 | Jugar 3 turnos completos (robar del mazo o del pozo, organizar la mano, descartar) | 3 descartes registrados en el log |
| T3 | Intentar un **cierre inválido deliberado** y explicar con sus palabras el mensaje del sistema | Usuario parafrasea la causa correctamente |
| T4 | Lograr un **cierre válido** | Evento `cierre_intentado` con `valido=true` |
| T4b | (Opcional) Dejar vencer el temporizador y observar la acción por defecto | Evento `turno_expirado` |
| T5 | (Apuntado) Jugar rondas consecutivas hasta que alguien supere 101 y leer el resultado final | Usuario identifica quién perdió y por qué |

> Tip para la demo y T4: crear la partida con una semilla fija vía API
> (`"seed": 42`, `"turn_seconds": 0` para desactivar el temporizador) permite repetir el mismo reparto entre sesiones.

## Métricas

| Métrica | Fuente |
|---|---|
| Tasa de éxito en cierre (T4) | `python -m scripts.session_report --url http://127.0.0.1:8000 --csv docs/validacion/evidencias/logs/metricas_sistema.csv` |
| Cierres inválidos y su causa | mismo reporte (`causas_rechazo`) |
| Tiempo promedio por turno | mismo reporte (`tiempo_promedio_turno_s`) |
| Latencia percibida | indicador "Latencia" en la barra superior + pregunta de la encuesta |
| Errores / confusiones de regla | notas del observador |
| Satisfacción | SUS (10 ítems) + calificación 1-5 → `encuesta_SUS.md` |

## Después de la sesión
1. Exportar la base: `docker compose exec -T postgres pg_dump -U apuntado apuntado > docs/validacion/evidencias/logs/apuntado.sql`.
2. Exportar el registro de cada partida: `GET /api/games/{id}/events` → guardar como JSON.
3. Generar el CSV de métricas con `scripts.session_report`.
4. Llenar `resultados.csv` (tabla consolidada 3.3) y calcular SUS.
5. Escribir el plan de mejoras (3.4) en `mejoras.md`, enlazando cada mejora con una observación.
