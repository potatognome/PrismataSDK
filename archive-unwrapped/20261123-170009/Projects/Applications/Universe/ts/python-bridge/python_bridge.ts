// Canonical Universe Python Bridge
// Thin TypeScript boundary for Python-backed runtime operations.

import * as path from "path";
import * as fs from "fs";
import { spawnSync } from "child_process";

function resolveBridgePath(): string {
    return path.resolve(__dirname, "../../python/python_bridge.py");
}

function resolvePythonExecutable(): string {
    const candidates = [
        path.resolve(__dirname, "../../../../../.venv/Scripts/python.exe"),
        path.resolve(__dirname, "../../../../.venv/Scripts/python.exe"),
    ];

    for (const candidate of candidates) {
        if (fs.existsSync(candidate)) {
            return candidate;
        }
    }

    return "python";
}

export async function pythonExecute(command: string, payload: any): Promise<any> {
    const bridgePath = resolveBridgePath();
    const pythonExe = resolvePythonExecutable();
    const inputPayload = JSON.stringify(payload ?? {});

    const runner = [
        "import importlib.util, json, sys",
        "bridge_path = sys.argv[1]",
        "cmd = sys.argv[2]",
        "payload = json.loads(sys.argv[3])",
        "spec = importlib.util.spec_from_file_location('universe_bridge', bridge_path)",
        "if spec is None or spec.loader is None:",
        "    raise RuntimeError(f'Unable to load bridge: {bridge_path}')",
        "mod = importlib.util.module_from_spec(spec)",
        "spec.loader.exec_module(mod)",
        "result = mod.execute(cmd, payload)",
        "print(json.dumps(result))",
    ].join("\n");

    const proc = spawnSync(pythonExe, ["-c", runner, bridgePath, command, inputPayload], {
        encoding: "utf8",
    });

    if (proc.error) {
        throw proc.error;
    }

    if (proc.status !== 0) {
        throw new Error((proc.stderr || "python bridge command failed").trim());
    }

    const stdout = String(proc.stdout ?? "").trim();
    if (!stdout) {
        return {};
    }

    return JSON.parse(stdout);
}
