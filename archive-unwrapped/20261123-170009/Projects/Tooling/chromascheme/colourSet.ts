import {
  ColourEntry,
  IColourSet,
} from "./interfaces";

/**
 * Immutable wrapper around a colourSet array.
 * Guarantees the source array is never mutated.
 */
export class ColourSet implements IColourSet {
  readonly entries: ReadonlyArray<ColourEntry>;

  private readonly _index: ReadonlyMap<string, ColourEntry>;

  constructor(entries: ColourEntry[]) {
    this.entries = Object.freeze([...entries]);
    const index = new Map<string, ColourEntry>();
    for (const entry of entries) {
      index.set(entry.id, entry);
    }
    this._index = index;
  }

  get(id: string): ColourEntry | null {
    return this._index.get(id) ?? null;
  }
}
