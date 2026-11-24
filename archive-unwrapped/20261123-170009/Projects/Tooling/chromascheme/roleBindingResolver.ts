import {
  IRoleBindings,
  RoleBindings,
  RoleLayerEntry,
} from "./interfaces";

/**
 * Typed, read-only wrapper around a RoleBindings map.
 * Roles remain semantic (not positional); the underlying object is frozen
 * to prevent accidental mutation.
 */
export class RoleBindingResolver implements IRoleBindings {
  readonly roles: Readonly<RoleBindings>;

  constructor(roles: RoleBindings) {
    this.roles = Object.freeze({ ...roles });
  }

  getRole(name: keyof RoleBindings): RoleLayerEntry | null {
    return this.roles[name] ?? null;
  }
}
