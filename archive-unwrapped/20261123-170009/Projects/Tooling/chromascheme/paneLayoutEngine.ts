import {
  IFractalQuadrantMapper,
  IPaneLayoutEngine,
  PaneModel,
  PaneRect,
  RenderedPane,
  IColourRefResolver,
} from "./interfaces";

/**
 * Computes pixel/character-space layout for a set of pane models.
 * Uses a FractalQuadrantMapper to derive normalised rects, then scales
 * them to the provided totalWidth × totalHeight canvas.
 * Does not mutate the input pane models.
 */
export class PaneLayoutEngine implements IPaneLayoutEngine {
  private readonly _mapper: IFractalQuadrantMapper;
  private readonly _resolver: IColourRefResolver;

  constructor(mapper: IFractalQuadrantMapper, resolver: IColourRefResolver) {
    this._mapper = mapper;
    this._resolver = resolver;
  }

  computeLayout(panes: PaneModel[], totalWidth: number, totalHeight: number): RenderedPane[] {
    return panes.map(pane => {
      const normalised: PaneRect = this._mapper.map(pane.fractalPosition);

      const rect: PaneRect = {
        x:      Math.round(normalised.x * totalWidth),
        y:      Math.round(normalised.y * totalHeight),
        width:  Math.round(normalised.width  * totalWidth),
        height: Math.round(normalised.height * totalHeight),
      };

      const bgColour   = pane.layers.bg     ? this._resolver.resolve(pane.layers.bg.colourRef)     : null;
      const borderColour = pane.layers.border ? this._resolver.resolve(pane.layers.border.colourRef) : null;

      return {
        role: pane.role,
        rect,
        bgColour:     bgColour     ? bgColour.rgb     : null,
        borderColour: borderColour ? borderColour.rgb : null,
      };
    });
  }
}
