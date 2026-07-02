# Runtime Method Core Source

## Provenance

- Supplied source directory: `TraceShield_Experiment-main/TraceShield_Experiment-main/`
- Imported package: `traceshield_experiment_core/`
- Import date: 2026-07-02
- TraceShield integration base: `frontend@c18ffc4590bacf957428d5bab3e032474945e89d`
- Deterministic source-package SHA-256: `11118c7d1d0bd397ec20d409e9fa513dd8790bb4ce88d23f5863605d12c0f698`

The source-package hash is computed from the sorted relative path and SHA-256 of every file under `traceshield_experiment_core/`.

## Included

- Method evaluator and schemas
- Boundary, correlation, detector, semantic, state, and reporting modules
- Tool semantic mapper
- Method-owned YAML configuration
- NeMo adapter templates already contained inside the method package
- Original method-core README
- Focused method tests and equivalent isolated evaluator, mapper, and state tests

## Excluded

- `data/`
- `experiments/`
- `paper/`
- `dataset_processors/`
- `sc_guard/` legacy experiment package
- Dataset and experiment scripts
- `scikit-learn` and `rich`, which are not imported by the method core

## Package Path Adjustment

The package moved from:

```text
traceshield_experiment_core
```

to:

```text
traceshield_method.method
```

Absolute imports and README usage examples were updated mechanically. Evaluator, boundary, detector, correlation, state, and risk-graph behavior was not changed.

Three legacy tests originally targeted `sc_guard`. Equivalent isolated tests now target the imported method package and its package-owned configuration. The assertions remain focused on evaluator decisions, tool mapping, and trace state.

## Licensing Note

No `LICENSE`, `NOTICE`, or `COPYING` file was present in the supplied source tree. The original method README and this provenance record are retained. A license must be confirmed with the source owner before redistribution.

## Post-Import Integration Delta

Phase 0 preserved the method-owned YAML files byte-for-byte. During the later Core v2 integration, `method/configs/tool_registry.yaml` intentionally moved to registry version `v2` by adding the local read-only `traceshield_status` tool. Runtime protocol responses now report `registry_version: v2`.

This is a product integration mapping change only. The imported evaluator, boundary, correlation, detector, state, and risk-graph implementation remains behaviorally unchanged from the Phase 0 import.
