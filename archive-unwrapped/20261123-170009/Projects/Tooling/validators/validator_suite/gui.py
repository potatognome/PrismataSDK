import tkinter as tk
from tkinter import ttk
from Projects.Tooling.validators.validator_suite.runner import run_all_validators, fix_all

class ValidatorDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Prismata Validator Suite')
        self.geometry('900x600')

        self.results = None
        self.create_widgets()

    def create_widgets(self):
        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        ttk.Label(left, text='Validators').pack(anchor='w')

        self.validator_list = tk.Listbox(left, height=10)
        self.validator_list.pack(fill=tk.X)
        self.validator_list.bind('<<ListboxSelect>>', self.on_validator_selected)

        self.validator_list.insert(tk.END, 'Casing Validator')
        self.validator_list.insert(tk.END, 'BOM Validator')

        ttk.Button(left, text='Run All', command=self.run_all).pack(fill=tk.X, pady=5)
        ttk.Button(left, text='Fix All', command=self.fix_all).pack(fill=tk.X, pady=5)

        right = ttk.Frame(self)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(right, text='Details').pack(anchor='w')

        self.text = tk.Text(right, wrap='none')
        self.text.pack(fill=tk.BOTH, expand=True)

    def run_all(self):
        self.results = run_all_validators()
        self.text.delete('1.0', tk.END)
        self.text.insert(tk.END, 'Validators executed.\nSelect a validator to view details.')

    def fix_all(self):
        if not self.results:
            self.text.insert(tk.END, '\nRun validators first.')
            return

        fix_all(self.results)
        self.text.insert('1.0', 'All fixes applied.\n')

    def on_validator_selected(self, event=None):
        if not self.results:
            return

        idx = self.validator_list.curselection()
        if not idx:
            return

        name = self.validator_list.get(idx[0])
        self.text.delete('1.0', tk.END)

        if name == 'Casing Validator':
            issues = self.results['casing']['issues']
            self.text.insert(tk.END, f'Casing Issues: {len(issues)}\\n\\n')
            for path, key, casing in issues:
                self.text.insert(tk.END, f'{path}: {key} ? {casing}\\n')

        elif name == 'BOM Validator':
            issues = self.results['bom']['issues']
            self.text.insert(tk.END, f'BOM Issues: {len(issues)}\\n\\n')
            for path in issues:
                self.text.insert(tk.END, f'{path}\\n')
