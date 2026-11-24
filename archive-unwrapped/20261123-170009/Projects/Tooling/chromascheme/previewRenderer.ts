import {
  FrameBuffer,
  IPreviewRenderer,
  PaneModel,
  RenderedPane,
} from "./interfaces";
import { FractalQuadrantMapper } from "./fractalQuadrantMapper";
import { PaneLayoutEngine } from "./paneLayoutEngine";
import { IColourRefResolver } from "./interfaces";

/**
 * Produces a deterministic FrameBuffer from a set of pane models.
 * Rendering is pure: no I/O, no content, no side-effects.
 * The default canvas is 80×24 (character units).
 */
export class PreviewRenderer implements IPreviewRenderer {
  private readonly _layoutEngine: PaneLayoutEngine;
  private readonly _totalWidth: number;
  private readonly _totalHeight: number;

  constructor(
    resolver: IColourRefResolver,
    options?: { totalWidth?: number; totalHeight?: number }
  ) {
    const mapper = new FractalQuadrantMapper();
    this._layoutEngine = new PaneLayoutEngine(mapper, resolver);
    this._totalWidth  = options?.totalWidth  ?? 80;
    this._totalHeight = options?.totalHeight ?? 24;
  }

  render(panes: PaneModel[]): FrameBuffer {
    const rendered: RenderedPane[] = this._layoutEngine.computeLayout(
      panes,
      this._totalWidth,
      this._totalHeight
    );
    return rendered;
  }
}
