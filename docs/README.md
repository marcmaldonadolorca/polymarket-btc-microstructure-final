# Guía de lectura de `docs/`

Estos documentos son una versión curada del cuaderno de investigación usado para
construir la memoria. Su función es explicar el arco experimental, no publicar
cada artefacto interno generado durante el trabajo.

## Qué está completo y es canónico

Para seguir la narrativa principal basta con leer, en este orden:

1. `01_sistema_de_datos.md`
2. `04_splits_validacion_temporal.md`
3. `07_stress_de_latencia.md`
4. `10_secuencias_y_orderbook.md`
5. `11_correccion_score_adverse.md`
6. `14_especialista_prestart_h60.md`
7. `16_validacion_fresh.md`
8. `18_paper_shadow.md`

La memoria oficial está en `reports/memoria.pdf`. Si hay una diferencia de
redacción entre un documento histórico y la memoria, la memoria manda.

## Qué no se publica

Algunos documentos conservan referencias a nombres originales de notebooks,
scripts o directorios de `data/experiments/` que pertenecían al workspace
privado. Esos artefactos no se publican porque:

- dependen del corpus completo privado;
- son ramas exploratorias no necesarias para auditar la entrega;
- o duplican pasos resumidos en los notebooks pedagógicos publicados.

Esto es deliberado: el repositorio público contiene el código, las decisiones y
la evidencia necesaria para auditar las cifras finales, pero no el corpus
completo ni cada ejecución intermedia.

## Notebooks públicos

Los notebooks publicados son pedagógicos: resumen el camino del proyecto sin
exigir el workspace privado completo. El notebook final
`notebooks/08_auditoria_final_ledger.ipynb` trabaja solo con el ledger
anonimizado y permite verificar las cifras de la memoria.

## Auditoría final reproducible

Las cifras finales se pueden recalcular desde el ledger público con:

```bash
python scripts/experiments/recompute_final_summary_from_public_ledger.py --check
```

Ese comando no necesita el corpus privado ni modelos entrenados.
