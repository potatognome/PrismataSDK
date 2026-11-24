import * as path from "path";
import * as readline from "readline";
import * as fs from "fs";

interface BorderPatternMapping {
  TOP: string[] | string;
  BOTTOM: string[] | string;
  LEFT: string[] | string;
  RIGHT: string[] | string;
}

export type ColourKey =
  | "!data"
  | "!list"
  | "!text"
  | "!path"
  | "!done"
  | "!warn"
  | "!error"
  | "!help"
  | "!selection"
  | "!tableBorder"
  | "!tableHeader"
  | "!tableRows"
  | "!tableCurrentRow"
  | "!tableActiveSelection"
  | "!reset";

export interface MenuOption {
  key: string;
  label: string;
}

export interface SelectionTableRow {
  key: string;
  label: string;
  value?: string;
}

export interface HeaderOptions {
  isMainMenu?: boolean;
  width?: number;
}

export interface CliMenuPrimitivesOptions {
  writeLine?: (line: string) => void;
  basePath?: string;
}

const ANSI: Record<ColourKey, string> = {
  "!data": "\u001b[36m",
  "!list": "\u001b[32m",
  "!text": "\u001b[37m",
  "!path": "\u001b[34m",
  "!done": "\u001b[32m",
  "!warn": "\u001b[33m",
  "!error": "\u001b[31m",
  "!help": "\u001b[35m",
  "!selection": "\u001b[96m",
  "!tableBorder": "\u001b[35m",
  "!tableHeader": "\u001b[37m",
  "!tableRows": "\u001b[34m",
  "!tableCurrentRow": "\u001b[33m",
  "!tableActiveSelection": "\u001b[95m",
  "!reset": "\u001b[0m",
};

function withAnsi(colour: ColourKey, text: string): string {
  if (colour === "!reset") {
    return text;
  }

  return `${ANSI[colour]}${text}${ANSI["!reset"]}`;
}

export class CliMenuPrimitives {
  private readonly writeLine: (line: string) => void;
  private readonly basePath: string;
  private readonly sharedUiConfigFiles:
    | { coloursJson?: string; borderPatternsJson?: string }
    | undefined;

  constructor(options?: CliMenuPrimitivesOptions) {
    this.writeLine = options?.writeLine ?? console.log;
    this.basePath = path.resolve(options?.basePath ?? process.cwd());
    this.sharedUiConfigFiles = this.resolveSharedUiConfigFiles();
  }

  private resolveSharedUiConfigFiles(): { coloursJson?: string; borderPatternsJson?: string } | undefined {
    const candidates = [
      path.join(this.basePath, ".workspace", ".projects_config", "GLOBAL_SHARED.d"),
      path.join(path.resolve(this.basePath, ".."), "tUilKit", ".workspace", ".projects_config", "GLOBAL_SHARED.d"),
    ];

    const configDir = candidates.find(candidate => fs.existsSync(candidate));
    if (!configDir) {
      return undefined;
    }

    const coloursJson = path.join(configDir, "COLOURS.json");
    const borderPatternsJson = path.join(configDir, "BORDER_PATTERNS.json");

    return {
      coloursJson: fs.existsSync(coloursJson) ? coloursJson : undefined,
      borderPatternsJson: fs.existsSync(borderPatternsJson) ? borderPatternsJson : undefined,
    };
  }

  private readJsonIfExists(filePath?: string): Record<string, unknown> | undefined {
    if (!filePath || !fs.existsSync(filePath)) {
      return undefined;
    }

    try {
      const raw = fs.readFileSync(filePath, "utf8");
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : undefined;
    } catch {
      return undefined;
    }
  }

  private getBorderPattern(): BorderPatternMapping {
    const borderConfig = this.readJsonIfExists(this.sharedUiConfigFiles?.borderPatternsJson);
    const borderRegistry = (borderConfig?.BORDER_PATTERNS as Record<string, unknown> | undefined) ?? {};
    const preferred =
      borderRegistry.SINGLE_LINE ??
      borderRegistry.DOUBLE_LINE ??
      borderRegistry.ROUNDED ??
      borderRegistry.ASCII_BOX ??
      borderRegistry.BOLD ??
      borderRegistry.DASHED ??
      { TOP: ["="], BOTTOM: ["="], LEFT: ["|"], RIGHT: ["|"] };

    const shape = preferred as Record<string, unknown>;

    return {
      TOP: this.asStringArray(shape.TOP) ?? ["="],
      BOTTOM: this.asStringArray(shape.BOTTOM) ?? ["="],
      LEFT: this.asStringArray(shape.LEFT) ?? ["|"],
      RIGHT: this.asStringArray(shape.RIGHT) ?? ["|"],
    };
  }

  private asStringArray(value: unknown): string[] | undefined {
    if (Array.isArray(value)) {
      return value.map(part => String(part));
    }
    if (typeof value === "string") {
      return [value];
    }
    return undefined;
  }

  private renderBorderSegment(segment: string[] | string, width: number): string {
    const values = Array.isArray(segment) ? segment : [segment];
    const first = values[0] ?? "=";

    if (values.length >= 3) {
      const [left, fill, right] = values;
      return `${left}${fill.repeat(Math.max(width - 2, 0))}${right}`;
    }

    return `${first.repeat(Math.max(width, 0))}`;
  }

  colourLog(colour: ColourKey, ...parts: Array<string | number | boolean | null | undefined>): void {
    const text = parts
      .map(part => (part === null || part === undefined ? "" : String(part)))
      .join(" ")
      .trim();
    this.writeLine(withAnsi(colour, text));
  }

  displayHeader(title: string, options?: HeaderOptions): void {
    const width = options?.width ?? 64;
    const border = "=".repeat(width);
    const suffix = options?.isMainMenu ? " (Main Menu)" : "";

    this.writeLine(withAnsi("!data", border));
    this.writeLine(withAnsi("!text", `Universe - ${title}${suffix}`));
    this.writeLine(withAnsi("!data", border));
    this.writeLine("");
  }

  printOptions(options: MenuOption[]): void {
    for (const option of options) {
      this.writeLine(`${withAnsi("!list", option.key)}) ${withAnsi("!text", option.label)}`);
    }
    this.writeLine("");
  }

  renderSelectionTable(
    title: string,
    rows: SelectionTableRow[],
    options?: { width?: number; showUpdateHelp?: boolean; showHeader?: boolean }
  ): void {
    const tableWidth = options?.width ?? 72;
    const valueWidth = Math.max(12, tableWidth - 28);
    const labelWidth = Math.max(...rows.map(row => row.label.length), 18);
    const borderPattern = this.getBorderPattern();
    const leftPad = Array.isArray(borderPattern.LEFT) ? borderPattern.LEFT[0] ?? "|" : borderPattern.LEFT;
    const rightPad = Array.isArray(borderPattern.RIGHT) ? borderPattern.RIGHT[0] ?? "|" : borderPattern.RIGHT;

    const topLine = this.renderBorderSegment(borderPattern.TOP, tableWidth);
    const bottomLine = this.renderBorderSegment(borderPattern.BOTTOM, tableWidth);

    const showHeader = options?.showHeader !== false;
    if (showHeader) this.displayHeader(title, { isMainMenu: false });
    this.writeLine(withAnsi("!tableBorder", topLine));
    const showHelp = options?.showUpdateHelp !== false;
    if (showHelp) {
      this.writeLine(withAnsi("!help", `Select an item to update its default path.`));
    }
    this.writeLine("");

    for (const [index, row] of rows.entries()) {
      const value = row.value && row.value.trim() ? row.value : "(not set)";
      const left = `${row.label}`.padEnd(labelWidth, " ");
      const right = value.length > valueWidth ? `${value.slice(0, valueWidth - 1)}…` : value;
      const rowText = `${withAnsi("!list", String(index + 1))}. ${withAnsi("!text", left)} ${withAnsi("!tableBorder", "| ")} ${withAnsi("!path", right)}`;
      this.writeLine(`${withAnsi("!tableBorder", `${leftPad} `)}${rowText}${withAnsi("!tableBorder", ` ${rightPad}`)}`);
    }

    this.writeLine(withAnsi("!tableBorder", bottomLine));
    this.writeLine("");
  }

  async promptSelectionTable(
    rl: readline.Interface,
    rows: SelectionTableRow[],
    message = "Select item to update"
  ): Promise<SelectionTableRow | undefined> {
    if (rows.length === 0) {
      return undefined;
    }

    const currentSelection = { index: 0 };

    const promptText = `${message} (1-${rows.length}) [${currentSelection.index + 1}]`;
    this.writeLine("");
    this.writeLine(withAnsi("!selection", `${promptText}: ${rows[currentSelection.index].label}`));
    this.writeLine(withAnsi("!help", "Enter a number to select, any other key to cancel."));

    const answer = await this.promptInput(rl, promptText, true);

    // Blank input -> select current default
    if (!answer) {
      return rows[currentSelection.index];
    }

    const trimmed = answer.trim();
    if (!/^[0-9]+$/.test(trimmed)) {
      // Non-numeric input cancels
      return undefined;
    }

    const num = Number.parseInt(trimmed, 10);
    if (Number.isNaN(num) || num < 1 || num > rows.length) return undefined;

    return rows[num - 1];
  }

  cpath(value: string): string {
    const resolved = path.resolve(value);
    const relative = path.relative(this.basePath, resolved).replace(/\\/g, "/");

    if (!relative || relative.startsWith("..")) {
      return withAnsi("!path", resolved.replace(/\\/g, "/"));
    }

    return withAnsi("!path", `./${relative}`);
  }

  renderSchemaView(schemaId: string, properties: Array<{ key: string; type: string }>): void {
    this.displayHeader(schemaId);
    for (const property of properties) {
      this.writeLine(`${withAnsi("!list", "-")} ${withAnsi("!text", property.key)}: ${withAnsi("!data", property.type)}`);
    }
    this.writeLine("");
  }

  promptInput(
    rl: readline.Interface,
    message: string,
    allowEmpty = false
  ): Promise<string | undefined> {
    return new Promise(resolve => {
      rl.question(`${message}: `, answer => {
        const trimmed = answer.trim();
        if (!trimmed && !allowEmpty) {
          resolve(undefined);
          return;
        }

        resolve(trimmed);
      });
    });
  }

  async promptMultiInput(
    rl: readline.Interface,
    message: string,
    options?: { allowCommaSeparated?: boolean }
  ): Promise<string[] | undefined> {
    const allowComma = options?.allowCommaSeparated ?? true;

    // First prompt accepts comma-separated values for convenience.
    const first = await this.promptInput(rl, `${message} (enter comma-separated or press Enter to input multiple)` , true);
    if (typeof first === "string" && first.trim()) {
      if (allowComma && first.includes(",")) {
        return first
          .split(",")
          .map(s => s.trim())
          .filter(Boolean);
      }
      // Single value provided — return as single-element array
      return [first.trim()];
    }

    // Otherwise, collect multiple values until empty line
    const results: string[] = [];
    while (true) {
      const next = await this.promptInput(rl, `${message} (blank to finish)`, true);
      if (!next || !next.trim()) break;
      results.push(next.trim());
    }

    if (results.length === 0) return undefined;
    return results;
  }

  async confirmAction(
    rl: readline.Interface,
    message: string,
    defaultValue = false
  ): Promise<boolean> {
    const prompt = defaultValue ? `${message} (Y/n)` : `${message} (y/N)`;
    const response = await this.promptInput(rl, prompt, true);

    if (!response) {
      return defaultValue;
    }

    const normalized = response.toLowerCase();
    return normalized === "y" || normalized === "yes";
  }
}
