# KADD and Repository Boundaries

PrismataCore is the source of truth for canonical definitions and architectural
intent. Read KADD before making architectural decisions.

- Core defines identity, structure, schemas, laws, manifests, and validation.
- SDK implements loading, resolution, composition, execution, rendering, and tools.
- Corp governs tenants, workspaces, archives, policy, stewardship, and preservation.

SDK agents must not copy canonical definitions into SDK code or invent a competing
schema. Load and validate Core definitions, then construct SDK runtime objects.

The former combined Prismata repository may provide migration context, examples,
and legacy behavior only. It has no normative architectural authority.
