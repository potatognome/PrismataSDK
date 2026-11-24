import tkinter as tk
from tkinter import ttk
from .core.schema_loader import load_all_schemas
from .core.registry_loader import load_registry
from .core.dependency_extractor import extract_dependencies_from_schema, analyze_manifest
from .core.renderer_simulator import simulate_renderer
from .core.utils import flatten_registry

def run_gui():
    schemas = load_all_schemas()
    registry = load_registry()

    app = PrismataVisualizer(registry, schemas)
    app.mainloop()

class PrismataVisualizer(tk.Tk):
    def __init__(self, registry, schemas):
        super().__init__()
        self.title("Prismata Dependency & Renderer Visualizer")
        self.geometry("900x600")

        self.registry = registry
        self.schemas = schemas

        self.create_widgets()

    def create_widgets(self):
        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(left, text="Manifest Type").pack(anchor="w")
        self.type_var = tk.StringVar()
        type_combo = ttk.Combobox(left, textvariable=self.type_var,
                                  values=list(self.registry.keys()))
        type_combo.pack(fill=tk.X)
        type_combo.bind("<<ComboboxSelected>>", self.on_type_selected)

        self.listbox = tk.Listbox(left)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_manifest_selected)

        right = ttk.Frame(self)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.text = tk.Text(right, wrap="none")
        self.text.pack(fill=tk.BOTH, expand=True)

    def on_type_selected(self, event=None):
        mtype = self.type_var.get()
        self.listbox.delete(0, tk.END)
        for entry_id in self.registry.get(mtype, {}):
            self.listbox.insert(tk.END, entry_id)

    def on_manifest_selected(self, event=None):
        idx = self.listbox.curselection()
        if not idx:
            return

        mtype = self.type_var.get()
        entry_id = self.listbox.get(idx[0])

        schema = self.schemas.get(mtype)
        deps = extract_dependencies_from_schema(schema) if schema else []
        manifest_file = self.registry[mtype][entry_id]["file"]

        dep_graph = analyze_manifest(manifest_file, deps, flatten_registry(self.registry))
        sim = simulate_renderer(mtype, entry_id, self.registry)

        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, dep_graph)
        self.text.insert(tk.END, "\n\n")
        self.text.insert(tk.END, sim)
