# Structural UI Instructions

Implement structure before styling.

## Ownership

- Framework: presentation topology and pane composition
- Pane: addressable presentation slot and output target
- Menu: capability invocation routing
- Capability: functional behavior and output
- Renderer: adaptive presentation of functional output

## Required Sequence

1. Framework discovery and loading
2. Pane discovery and location resolution
3. Menu and menu-item resolution
4. Capability resolution and execution
5. Functional output injection
6. Rendering and preview

Do not embed capability behavior in panes or infer runtime placement inside
capabilities. Keep border patterns, chroma, colour roles, and ANSI rendering
behind the structural gate.
