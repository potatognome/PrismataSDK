import {
  GeometryDescriptor,
  IGeometryDescriptor,
} from "./interfaces";

/**
 * Interprets ChromaScheme geometry metadata without coupling to rendering.
 * Keeps geometry logic decoupled from role bindings and colour resolution.
 */
export class GeometryInterpreter implements IGeometryDescriptor {
  readonly descriptor: Readonly<GeometryDescriptor>;

  constructor(descriptor: GeometryDescriptor) {
    this.descriptor = Object.freeze({
      baseGeometry: descriptor.baseGeometry,
      overlays: Object.freeze([...descriptor.overlays]),
    });
  }

  overlayTypes(): string[] {
    return this.descriptor.overlays.map(o => o.type);
  }
}
