import { parsePrompt } from "./parser";
import { scanAPIsRecursive } from "./api-scanner";

function main() {
  const target = process.argv[2] || ".";
  const apiScan = scanAPIsRecursive(target);
  // Emit JSON only so wrappers can parse summaries deterministically.
  console.log(JSON.stringify(apiScan, null, 2));
}

main();
