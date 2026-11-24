import {
  FractalPosition,
  IFractalQuadrantMapper,
  PaneRect,
} from "./interfaces";

/**
 * Maps FractalPosition tokens to normalised PaneRects within [0,1]×[0,1].
 *
 * Quadrant layout (top-left origin):
 *   Q1 = top-left     Q2 = top-right
 *   Q3 = bottom-left  Q4 = bottom-right
 *
 * Nested notation (e.g. "Q1:Q2") subdivides the parent quadrant using
 * the same rule recursively at half scale.
 */
export class FractalQuadrantMapper implements IFractalQuadrantMapper {
  /**
   * Base quadrant rects in normalised [0,1]×[0,1] space.
   */
  private static readonly BASE_QUADS: Readonly<Record<string, PaneRect>> = {
    Q1: { x: 0,    y: 0,    width: 0.5, height: 0.5 },
    Q2: { x: 0.5,  y: 0,    width: 0.5, height: 0.5 },
    Q3: { x: 0,    y: 0.5,  width: 0.5, height: 0.5 },
    Q4: { x: 0.5,  y: 0.5,  width: 0.5, height: 0.5 },
  };

  map(position: FractalPosition): PaneRect {
    const parts = position.split(":");

    let rect: PaneRect = { x: 0, y: 0, width: 1, height: 1 };

    for (const part of parts) {
      const base = FractalQuadrantMapper.BASE_QUADS[part];
      if (!base) {
        throw new Error(`Unknown quadrant token: "${part}" in position "${position}"`);
      }
      rect = {
        x:      rect.x + base.x * rect.width,
        y:      rect.y + base.y * rect.height,
        width:  base.width  * rect.width,
        height: base.height * rect.height,
      };
    }

    return rect;
  }
}
