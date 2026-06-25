# Puertas de riesgo y transición al diagnóstico de volatilidad

Fecha de corte histórica: 2026-06-02.
Estado final del documento: contexto metodológico, no evidencia confirmatoria.

Este archivo conserva el nombre `15_vol_gate.md` por continuidad con la memoria y
con `config/frozen_policy_thresholds.yaml`, pero su papel correcto es explicar la
transición entre el especialista `prestart H60` y el diagnóstico final de
volatilidad. La validación fuera de muestra limpia y el diagnóstico post-hoc se
documentan en `docs/16_validacion_fresh.md`.

## 1. Problema detectado

El especialista `prestart H60` tenía señal agregada, pero no estabilidad diaria
suficiente. En el bloque histórico de test aparecía un día malo que no se
arreglaba simplemente subiendo los umbrales del modelo.

La pregunta de esta fase era:

```text
¿podemos saber cuándo no operar sin mirar el futuro?
```

Esta pregunta es distinta de entrenar un predictor más potente. El problema ya
no era solo encontrar filas con valor esperado, sino detectar si el entorno de
ejecución era favorable.

## 2. Puertas de riesgo probadas antes del bloque fresh

Se probaron puertas simples basadas en los scores del especialista:

- umbrales más estrictos de EV;
- umbrales más estrictos de probabilidad de relleno sano;
- consenso entre variantes del modelo;
- diferencia máxima entre predicciones;
- uso conservador del mínimo entre modelos.

La lectura fue negativa:

```text
NO_GO_RISK_GATE
```

Algunas reglas parecían arreglar el test histórico, pero fallaban los criterios
de validación. Aceptarlas habría sido elegir una regla porque arreglaba justo el
bloque observado, es decir, una forma de leakage metodológico.

## 3. Lección metodológica

La fase confirmó tres cosas:

1. Hay señal en `prestart H60`.
2. El problema no se resuelve solo con thresholds más duros.
3. Hace falta mirar el régimen de mercado de forma explícita.

Por eso el siguiente paso fue estudiar variables de régimen, especialmente la
volatilidad realizada del perpetuo. Esta variable ya existía en el conjunto de
características y su umbral operativo (`0.6657`) corresponde al percentil 80 del
entrenamiento.

## 4. Relación con el filtro final de volatilidad

El filtro final:

```text
perp_realized_vol_bps_5s <= 0.6657
```

no debe leerse como una segunda validación fuera de muestra. El valor numérico
procede del entrenamiento, pero la decisión de adoptarlo como filtro se tomó
después de inspeccionar el bloque del 6 al 10 de junio de 2026. Por eso la
memoria lo presenta como:

```text
POSTHOC_DIAGNOSTIC_PENDING_PROSPECTIVE_VALIDATION
```

La evidencia confirmatoria limpia sigue siendo el especialista base sin filtro:

| Alcance | n | @0.25 | @0.5 | @1.0 | Días positivos @0.5 |
|---|---:|---:|---:|---:|---:|
| Especialista base | 754 | +0.537 | +0.349 | -0.026 | 3/5 |

El subconjunto de baja volatilidad es una hipótesis prometedora, no una prueba
cerrada:

| Alcance | n | @0.25 | @0.5 | @1.0 | Días positivos @0.5 |
|---|---:|---:|---:|---:|---:|
| Baja volatilidad post-hoc | 318 | +1.258 | +1.069 | +0.691 | 5/5 |

## 5. Decisión final

La política completa queda congelada después del 10 de junio de 2026:

```text
EV > 0.75
HP >= 0.50
perp_realized_vol_bps_5s <= 0.6657
strict_45_60_early
```

Solo fechas posteriores, sin retocar umbrales, pueden convertir esta hipótesis
en validación prospectiva.
