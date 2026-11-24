/**
 * Shared interfaces for the Prismata ChromaScheme tooling primitives.
 * All rendering and resolution logic depends on these contracts.
 */

// ---------------------------------------------------------------------------
// Value types
// ---------------------------------------------------------------------------

export interface RgbColour {
  r: number;
  g: number;
  b: number;
}

export interface ColourEntry {
  id: string;
  origin?: string;
  rgb: RgbColour;
}

export interface ColourRef {
  colourRef: string;
}

export interface RoleLayerEntry {
  layers?: {
    bg?: ColourRef;
    fg?: ColourRef;
  };
}

export interface RoleBindings {
  primary_surface?:   RoleLayerEntry;
  secondary_surface?: RoleLayerEntry;
  tertiary_surface?:  RoleLayerEntry;
  accent_surface?:    RoleLayerEntry;
  border_fg?:         RoleLayerEntry;
  menu_fg?:           RoleLayerEntry;
  menu_bg?:           RoleLayerEntry;
  interactive_fg?:    RoleLayerEntry;
  interactive_bg?:    RoleLayerEntry;
  neutral_fg?:        RoleLayerEntry;
  neutral_bg?:        RoleLayerEntry;
}

export interface GeometryOverlay {
  type: string;
  params?: Record<string, unknown>;
}

export interface GeometryDescriptor {
  baseGeometry: string;
  overlays: GeometryOverlay[];
}

// ---------------------------------------------------------------------------
// Fractal position type (mirrors schema enum)
// ---------------------------------------------------------------------------

export type FractalPosition =
  | "Q1" | "Q2" | "Q3" | "Q4"
  | "Q1:Q1" | "Q1:Q2"
  | "Q2:Q1" | "Q2:Q2"
  | "Q3:Q1" | "Q3:Q2"
  | "Q4:Q1" | "Q4:Q2" | "Q4:Q3" | "Q4:Q4";

export interface PaneRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PaneModel {
  role: string;
  layers: {
    bg?: ColourRef;
    border?: ColourRef;
  };
  fractalPosition: FractalPosition;
  proportion: number;
}

export interface RenderedPane {
  role: string;
  rect: PaneRect;
  bgColour: RgbColour | null;
  borderColour: RgbColour | null;
}

export type FrameBuffer = RenderedPane[];

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

/** Resolves a ColourRef string to the matching ColourEntry in a colourSet. */
export interface IColourRefResolver {
  resolve(ref: string): ColourEntry | null;
}

/** Maps a FractalPosition token to a normalised PaneRect within [0,1]×[0,1]. */
export interface IFractalQuadrantMapper {
  map(position: FractalPosition): PaneRect;
}

/** Scales normalised PaneRects to pixel/character dimensions. */
export interface IPaneLayoutEngine {
  computeLayout(panes: PaneModel[], totalWidth: number, totalHeight: number): RenderedPane[];
}

/** Produces a FrameBuffer from a set of pane models and a resolved colourSet. */
export interface IPreviewRenderer {
  render(panes: PaneModel[]): FrameBuffer;
}

/** Typed wrapper around a read-only colourSet array. */
export interface IColourSet {
  readonly entries: ReadonlyArray<ColourEntry>;
  get(id: string): ColourEntry | null;
}

/** Typed wrapper around role bindings that prevents mutation. */
export interface IRoleBindings {
  readonly roles: Readonly<RoleBindings>;
  getRole(name: keyof RoleBindings): RoleLayerEntry | null;
}

/** Interprets geometry metadata without coupling it to rendering. */
export interface IGeometryDescriptor {
  readonly descriptor: Readonly<GeometryDescriptor>;
  overlayTypes(): string[];
}
