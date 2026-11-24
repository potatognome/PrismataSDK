// Prompt normalizer 
import { PromptAST } from "./model";

export function toMinimalPrompt(ast: PromptAST): string {
  const parts: string[] = [];

  if (ast.task) parts.push(ast.task);
  if (ast.inputs.length > 0) parts.push(`Input: ${ast.inputs.join("; ")}`);
  if (ast.context) parts.push(`Context: ${ast.context}`);
  if (ast.constraints.length > 0)
    parts.push(`Constraints: ${ast.constraints.join("; ")}`);
  if (ast.style) parts.push(`Style: ${ast.style}`);
  if (ast.output_format) parts.push(`Output: ${ast.output_format}`);

  return parts.join(" ");
}
