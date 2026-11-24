import { runCli } from "./cli/runCli";

runCli().catch(err => {
  console.error("Universe runtime failed:", err);
});
