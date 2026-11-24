# Prismata UDI Compliance Specification

## Last Updated: 2026-09-19

### Authoritative Identity Rules for All Artifact Generators, Validators, and Schemas

This document defines the **Universal Deterministic Identifier (UDI)** system for the Prismata ecosystem.  
All generators, validators, schema authors, and Copilot agents must follow this specification when creating, modifying, or validating Prismata artifacts.

UDIs are the **single source of truth** for artifact identity across all Prismata subsystems.

---

# 1. UDI Definition

A UDI is a **four‑segment**, **namespace‑prefixed**, **deterministic**, **immutable** identifier:

```
namespace.scope.kind.slug
```

Each segment has strict rules and must appear in the correct order.

---

# 2. Segment Rules

## 2.1 namespace
- Lowercase
- Typically `prismata`, `tenant-universe` or a named tenant-universe:
  - `prismata`
  - `tenant-universe`
  - `lumen`
  - `nebula`
- Never changes once assigned.

## 2.2 scope
- Lowercase
- Kebab‑case
- Must correspond to the subsystem or project folder path
- Examples:
  - `meta`
  - `universe`
  - `tooling`
  - `tenant-custom-project`

## 2.3 kind
Must be one of the **canonical UDI kinds**:

```
api-ref
ast-node
capability
chroma-scheme
colour-keys
colour-roles
colour-scheme
composition
config
document
function-ref
log-file
manifest
menu
menu-item
metadata
pane
pane-roles
registry
scan-result
schema
search-result
service
ui-framework
```

## 2.4 slug
- Lowercase
- Kebab‑case
- Max 64 characters
- Derived deterministically from:
  - `metadata.name`, or
  - file basename
- Forbidden:
  - randomness
  - timestamps
  - counters
  - uppercase
  - underscores
  - non‑alphanumeric symbols (except hyphens)

---

# 3. Canonical UDI Regex

All UDIs must match:

```
^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.[a-z][a-z0-9-]+$
```

---

# 4. Ordering Rules

The UDI segments must appear **exactly** in this order:

1. namespace  
2. scope  
3. kind  
4. slug  

Any deviation is invalid.

### INVALID_UDI_ORDERING examples:
- `prismata.meta.slug.kind`
- `prismata.schema.meta.my-slug`
- `prismata.menu-item.menu.my-item`

These must be reported as **INVALID_UDI_ORDERING**.

---

# 5. Determinism Rules

A UDI must be **derivable from content**.  
Two identical artifacts must produce identical UDIs.

Forbidden sources of entropy:
- random UUIDs
- timestamps
- counters
- hash digests
- environment‑dependent values

---

# 6. Immutability Rules

Once published:
- A UDI **must never change**
- Artifact evolution is handled through **version fields**, not UDI changes
- Changing a UDI is a **breaking change** requiring a major version bump

---

# 7. Required UDI Presence

All artifacts participating in Prismata tooling **must** have a UDI.

This includes:
- canonical schemas  
- project schemas  
- manifests  
- capabilities  
- menus  
- menu items  
- UI framework artifacts  
- panes  
- pane roles  
- colour schemes  
- chroma schemes  
- colour keys  
- colour roles  
- registries  
- scan results  
- log files  
- documents  
- compositions  
- metadata artifacts  
- config artifacts  

No artifact may be “anonymous”.

---

# 8. Drift Categories

Generators must avoid producing artifacts that fall into any of these drift categories.  
Validators must detect them.

## Critical Drift
- MISSING_UDI  
- INVALID_UDI_PATTERN  
- INVALID_NAMESPACE  
- INVALID_KIND  
- INVALID_UDI_ORDERING  
- UDI_COLLISION  

## High Drift
- INVALID_SCOPE  
- INVALID_SLUG  
- KIND_MISMATCH  

## Medium Drift
- SCOPE_MISMATCH  
- KIND_NOT_ALLOWED_FOR_PATH  
- REDUNDANT_ID  

## Low Drift
- MISSING_KIND  
- MISSING_METADATA_NAME  

---

# 9. Artifact Generator Requirements

Any generator producing Prismata artifacts must:

## 9.1 Always generate a valid UDI
- Derive namespace from ecosystem
- Derive scope from folder path
- Derive kind from artifact type
- Derive slug from metadata.name or filename

## 9.2 Always include metadata.name
Slug derivation depends on it.

## 9.3 Always include kind
Must match canonical kind vocabulary.

## 9.4 Always validate UDI ordering
Segments must not be swapped or misordered.

## 9.5 Always avoid redundant IDs
Generators must not produce:
- `id:`
- `schema_id:`
- `capability_id:`
- `menu_id:`
unless explicitly required as aliases.

## 9.6 Always produce deterministic slugs
Slug must be stable across runs.

## 9.7 Always produce UDI‑compliant manifests
Manifests must include:
- `udi`
- `version`
- `kind`
- `application`
- capability IDs using UDI format

---

# 10. UDI Regeneration Algorithm

Generators must follow this algorithm when creating or repairing UDIs:

1. **namespace**  
   - Use ecosystem root (`prismata`, `lumen`, etc.)

2. **scope**  
   - Extract from folder path  
   - Convert to kebab‑case

3. **kind**  
   - Use canonical kind vocabulary  
   - Must match artifact type

4. **slug**  
   - Lowercase  
   - Kebab‑case  
   - Derived from metadata.name or filename  
   - Strip illegal characters  
   - Truncate to 64 chars

5. **Assemble UDI**  
   ```
   namespace.scope.kind.slug
   ```

6. **Validate against regex**

7. **Check for collisions**

---

# 11. Cross‑Document Uniqueness

Validators must ensure no two artifacts share the same UDI.

---

# 12. Folder Path → Scope Mapping

Generators must map folder paths to scopes:

| Folder | Scope |
|--------|--------|
| `Meta/canonical/` | `meta` |
| `Projects/<name>/config/` | `<name>` |
| `ui-framework/` | `ui-framework` |
| `colour-schemes/` | `colour-scheme` |
| `chroma-schemes/` | `chroma-scheme` |
| `pane/` | `pane` |
| `pane-roles/` | `pane-roles` |
| `registry/` | `registry` |
| `log-files/` | `log-file` |

This mapping is deterministic.

---

# 13. Artifact Type → Kind Mapping

| Artifact Type | Kind |
|---------------|------|
| schema file | `schema` |
| manifest file | `manifest` |
| capability | `capability` |
| menu | `menu` |
| menu item | `menu-item` |
| AST node | `ast-node` |
| scan result | `scan-result` |
| API reference | `api-ref` |
| function reference | `function-ref` |
| search result | `search-result` |
| registry | `registry` |
| config | `config` |
| composition | `composition` |
| metadata | `metadata` |
| document | `document` |
| log file | `log-file` |
| pane | `pane` |
| pane roles | `pane-roles` |
| colour scheme | `colour-scheme` |
| chroma scheme | `chroma-scheme` |
| colour keys | `colour-keys` |
| colour roles | `colour-roles` |
| ui framework | `ui-framework` |

---

# 14. Enforcement Requirements

All generators and validators must:

- refuse to generate artifacts without UDIs  
- refuse to generate artifacts with invalid UDIs  
- refuse to generate artifacts with non‑canonical kinds  
- refuse to generate artifacts with invalid ordering  
- refuse to generate artifacts with non‑deterministic slugs  
- refuse to generate artifacts with redundant IDs  
- refuse to generate artifacts missing metadata.name  
- refuse to generate artifacts missing kind  

---

# 15. Summary

This document is the **authoritative identity specification** for Prismata.  
All generators, validators, and schema authors must follow it.

UDIs must be:
- present  
- correct  
- deterministic  
- immutable  
- unique  
- ordered correctly  
- kind‑aligned  
- scope‑aligned  
- slug‑derived  
- regex‑valid  
- drift‑free  

This is the foundation for all Prismata tooling.

