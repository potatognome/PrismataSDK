# Hello_UDI Implementation Instructions

The Hello_UDI plan is `docs/plans/hello_udi_milestone_plan.yaml`.
It is the sequencing and acceptance reference for the SDK vertical slice.

## Active Sequence

- M0: complete
- M1: complete
- M2: active next gate
- M3-M11: pending until dependencies pass

Do not implement later capabilities while M2 is incomplete.

## Structural Path

```text
Manifest
  -> Capability
  -> Framework
  -> Menu
  -> Pane
  -> Functional Output
  -> Rendered Presentation
```

## Rules

- Every artifact used by Hello_UDI must be CMF-enveloped and UDI-compliant.
- Runtime objects must derive from validated Core definitions.
- Menu items resolve capabilities and target panes.
- Capabilities emit functional output, not presentation instructions.
- Pane injectors place output; renderers present it.
- Styling and tenant features remain excluded from structural acceptance.
