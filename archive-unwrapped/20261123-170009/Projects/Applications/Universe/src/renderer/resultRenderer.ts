import * as fs from "fs";
import * as readline from "readline";
import { CliMenuPrimitives, SelectionTableRow } from "../../../../Tooling/primitives/typescript/menuPrimitives";
import { SearchResultItem } from "../search/searchEngine";

export async function renderResultsList(
  ui: CliMenuPrimitives,
  rl: readline.Interface,
  results: SearchResultItem[],
  context?: { searchParams?: any; paths?: Record<string, string> }
): Promise<SearchResultItem | undefined> {
  if (!results || results.length === 0) {
    ui.colourLog("!warn", "No search results to display.");
    return undefined;
  }
  const rows: SelectionTableRow[] = results.map((r, i) => ({
    key: String(i + 1),
    label: `${r.relativePath} (${r.extension}, ${r.sizeBytes} bytes)`,
    value: r.fullPath,
  }));

  const pageSize = 10;
  let page = 0;
  let selectedIndex = 0; // index within full results for preview

  const makeRowsForPage = (p: number) =>
    results.slice(p * pageSize, p * pageSize + pageSize).map((r, i) => ({
      key: String(p * pageSize + i + 1),
      label: `${r.relativePath} (${r.extension}, ${r.sizeBytes} bytes)`,
      value: r.fullPath,
    }));

  while (true) {
    const rows = makeRowsForPage(page);
    // Compact information header showing active search params and paths — show above the files
    const sp = context?.searchParams ?? {};
    const paths = context?.paths ?? {};
    const ft = Array.isArray(sp.fileTypes) && sp.fileTypes.length ? sp.fileTypes.join(",") : "None";
    const qs = Array.isArray(sp.queries) && sp.queries.length ? sp.queries.join(",") : "None";
    const ts = Array.isArray(sp.tags) && sp.tags.length ? sp.tags.join(",") : "None";
    const cOnly = sp.canonicalOnly ? "true" : "false";
    const rec = sp.recursive ? "true" : "false";

    ui.displayHeader("Search Results", { isMainMenu: false });

    // Compact boolean flags on one line
    ui.colourLog("!text", `Flags: canonicalOnly=${cOnly}  recursive=${rec}`);

    // Conditionally render list-based parameters only when present
    if (Array.isArray(sp.fileTypes) && sp.fileTypes.length) {
      ui.colourLog("!text", `File Type(s): ${sp.fileTypes.join(", ")}`);
    } else {
      ui.colourLog("!text", "No File Types selected. Displaying all eligible UTF-encoded files by default.");
    }

    if (Array.isArray(sp.queries) && sp.queries.length) {
      ui.colourLog("!text", `Text Query(s): ${sp.queries.join(", ")}`);
    }

    if (Array.isArray(sp.tags) && sp.tags.length) {
      ui.colourLog("!text", `Tags: ${sp.tags.join(", ")}`);
    }

    // Build list of search folders to display (support multiple)
    const searchFolders: string[] = [];
    if (Array.isArray(sp.projects) && sp.projects.length) {
      for (const p of sp.projects) searchFolders.push(String(p));
    } else if (paths && paths.project_scope) {
      // project_scope may be a string or array; normalize
      if (Array.isArray(paths.project_scope)) {
        for (const p of paths.project_scope) searchFolders.push(String(p));
      } else if (typeof paths.project_scope === "string" && paths.project_scope.trim()) {
        searchFolders.push(paths.project_scope);
      }
    }

    // If canonicalOnly is true, include canonical folder in search folders (if configured)
    if (sp.canonicalOnly && paths?.canonical_folder) {
      const cf = String(paths.canonical_folder);
      if (!searchFolders.includes(cf)) searchFolders.push(cf);
    }

    // Display Search Folders header (only these paths should be shown)
    ui.displayHeader("Search Folders", { isMainMenu: false });
    if (searchFolders.length === 0) {
      ui.colourLog("!text", "(No Search Folders selected — searching workspace by default)");
    } else {
      for (const sf of searchFolders) ui.colourLog("!text", `- ${sf}`);
    }

    // If canonicalOnly is enabled, show an informational note about canonical filtering
    if (sp.canonicalOnly) {
      ui.colourLog("!warn", "Canonical mode active — only canonical files will be returned (must be versioned, active, and have a UDI).");
    }

    ui.renderSelectionTable(
      `Search Results (Page ${page + 1} of ${Math.ceil(results.length / pageSize)})`,
      rows,
      { width: 100, showUpdateHelp: false, showHeader: false }
    );

    ui.colourLog("!help", "Enter a number to open, 'n' next page, 'p' previous page, 'q' cancel.");
    const answer = await ui.promptInput(rl, `Select item (page ${page + 1}) or command`, true);
    if (!answer || !answer.trim()) {
      // default to first item on page
      const defaultGlobal = page * pageSize;
      selectedIndex = Math.min(defaultGlobal, results.length - 1);
      return results[selectedIndex];
    }

    const a = answer.trim().toLowerCase();
    if (a === "q" || a === "quit") {
      return undefined;
    }
    if (a === "n" || a === "next") {
      if ((page + 1) * pageSize < results.length) {
        page += 1;
        selectedIndex = page * pageSize;
      } else {
        ui.colourLog("!help", "Already on last page.");
      }
      continue;
    }
    if (a === "p" || a === "prev" || a === "previous") {
      if (page > 0) {
        page -= 1;
        selectedIndex = page * pageSize;
      } else {
        ui.colourLog("!help", "Already on first page.");
      }
      continue;
    }
    if (a === "v" || a === "view") {
      // 'view' preview command removed from results list; advise user
      ui.colourLog("!warn", "Preview is disabled in the results list. Open an item to view its preview.");
      continue;
    }

    // numeric selection
    const num = Number.parseInt(a, 10);
    if (!Number.isNaN(num) && num >= 1 && num <= results.length) {
      selectedIndex = num - 1;
      return results[selectedIndex];
    }

    ui.colourLog("!warn", "Unrecognized input.");
  }
}

export function renderPreview(ui: CliMenuPrimitives, item: SearchResultItem, maxLines = 40) {
  ui.displayHeader("Preview");
  ui.colourLog("!path", item.fullPath);

  try {
    const content = fs.readFileSync(item.fullPath, "utf8");
    const lines = content.split(/\r?\n/).slice(0, maxLines);
    for (const line of lines) {
      ui.colourLog("!text", line);
    }
    if (content.split(/\r?\n/).length > maxLines) {
      ui.colourLog("!help", `... preview truncated (${maxLines} lines)`);
    }
  } catch (err) {
    ui.colourLog("!error", "Unable to read file for preview.");
  }
}

export async function renderVersionCarousel(
  ui: CliMenuPrimitives,
  rl: readline.Interface,
  versions: SearchResultItem[]
): Promise<SearchResultItem | undefined> {
  if (!versions || versions.length === 0) return undefined;

  let index = 0;
  while (true) {
    const current = versions[index];
    ui.displayHeader(`Version ${index + 1} of ${versions.length}`);
    ui.colourLog("!path", current.fullPath);
    ui.colourLog("!help", `Modified: ${current.modifiedAt.toISOString()} Size: ${current.sizeBytes}`);

    const cmd = await ui.promptInput(rl, "(n)ext, (p)revious, (o)pen preview, (q)uit", true);
    if (!cmd) break;
    const c = cmd.trim().toLowerCase();
    if (c === "n" || c === "next") {
      index = (index + 1) % versions.length;
      continue;
    }
    if (c === "p" || c === "prev" || c === "previous") {
      index = (index - 1 + versions.length) % versions.length;
      continue;
    }
    if (c === "o" || c === "open") {
      renderPreview(ui, current);
      await ui.promptInput(rl, "Press Enter to return to carousel", true);
      continue;
    }
    if (c === "q" || c === "quit") {
      break;
    }
  }

  return undefined;
}
