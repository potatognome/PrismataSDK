# SDK Testing Instructions

Prioritize tests that falsify structural contracts before adding visual coverage.

Required areas:

- CMF loading and validation
- Schema and manifest loading
- Registry discovery
- Capability resolution
- Framework composition
- Pane location resolution
- Menu routing
- Target pane injection
- Negative and invalid loader paths
- Hello_UDI end-to-end behavior

Use the smallest deterministic test for a behavior. Update examples when they no
longer demonstrate the supported runtime path.
