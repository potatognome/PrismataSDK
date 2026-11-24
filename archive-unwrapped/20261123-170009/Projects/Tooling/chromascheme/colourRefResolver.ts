import {
  ColourEntry,
  IColourRefResolver,
  IColourSet,
} from "./interfaces";

/**
 * Resolves ColourRef strings to their matching ColourEntry.
 * Deterministic: given the same colourSet, the same ref always resolves
 * to the same entry. The colourSet is never mutated.
 */
export class ColourRefResolver implements IColourRefResolver {
  private readonly _colourSet: IColourSet;

  constructor(colourSet: IColourSet) {
    this._colourSet = colourSet;
  }

  resolve(ref: string): ColourEntry | null {
    return this._colourSet.get(ref);
  }
}
