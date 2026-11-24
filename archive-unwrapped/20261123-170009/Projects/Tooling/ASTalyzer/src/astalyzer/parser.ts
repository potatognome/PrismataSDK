// TICCSEO prompt parser 
import { PromptAST, createEmptyAST } from "./model";

const MARKERS = {
  task: /^task\s*:\s*(.*)$/i,
  input: /^input\s*:\s*(.*)$/i,
  context: /^context\s*:\s*(.*)$/i,
  output_format: /^(output\s*format|output)\s*:\s*(.*)$/i,
  style: /^style\s*:\s*(.*)$/i,
  constraints: /^constraints\s*:\s*$/i,
  examples: /^examples?\s*:\s*$/i,
};

export function parsePrompt(raw: string): PromptAST {
  const ast = createEmptyAST();
  const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(Boolean);

  let mode: "constraints" | "examples" | null = null;

  for (const line of lines) {
    if (MARKERS.constraints.test(line)) {
      mode = "constraints";
      continue;
    }
    if (MARKERS.examples.test(line)) {
      mode = "examples";
      continue;
    }

    if (mode === "constraints" && line.startsWith("-")) {
      ast.constraints.push(line.slice(1).trim());
      continue;
    }
    if (mode === "examples" && line.startsWith("-")) {
      ast.examples.push(line.slice(1).trim());
      continue;
    }

    let matched = false;

    for (const key of Object.keys(MARKERS)) {
      const pattern = MARKERS[key as keyof typeof MARKERS];
      const m = line.match(pattern);
      if (!m) continue;

      matched = true;
      mode = null;

      switch (key) {
        case "task":
          ast.task = m[1].trim();
          break;
        case "input":
          ast.inputs.push(m[1].trim());
          break;
        case "context":
          ast.context = m[1].trim();
          break;
        case "output_format":
          ast.output_format = m[2].trim();
          break;
        case "style":
          ast.style = m[1].trim();
          break;
      }
      break;
    }
  }

  return ast;
}
