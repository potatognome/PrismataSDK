// TICCSEO AST model 
export interface PromptAST {
  udi?: string;
  task?: string;
  inputs: string[];
  context?: string;
  constraints: string[];
  style?: string;
  examples: string[];
  output_format?: string;
}

export const createEmptyAST = (): PromptAST => ({
  udi: undefined,
  task: undefined,
  inputs: [],
  context: undefined,
  constraints: [],
  style: undefined,
  examples: [],
  output_format: undefined,
});
