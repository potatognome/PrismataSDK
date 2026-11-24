export type MenuAction = "back" | "exit" | "quit" | "navigate" | "execute" | "noop";

export interface MenuActionDescriptor {
  action: MenuAction;
  target?: string;
  label?: string;
  description?: string;
}

export function defaultMenuAction(label: string): MenuActionDescriptor {
  return {
    action: "noop",
    label,
    description: "No action is defined for this menu item.",
  };
}

export function renderActionIterator(items: Array<{ key: string; label: string }>): string[] {
  return items.map(item => `${item.key}) ${item.label}`);
}

export function confirmBackOption(items: Array<{ key: string; label: string }>): Array<{ key: string; label: string }> {
  return [...items, { key: "0", label: "Back" }];
}
