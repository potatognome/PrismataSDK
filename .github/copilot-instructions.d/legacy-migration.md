# Legacy Migration Instructions

Do not reuse legacy Prismata interfaces verbatim.

Use this migration chain:

```text
Legacy Module
  -> CMF Wrapper
  -> CMF Object
  -> PSO
  -> SDK Runtime
```

Rules:

- Preserve implementation content in a CMF `content:` block.
- Derive known metadata deterministically.
- Replace ad hoc object lookup with manifests, UDIs, and registries.
- Separate migrated capability behavior from presentation.
- Preserve migration lessons and test the resulting runtime contract.
