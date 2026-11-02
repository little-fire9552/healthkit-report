// Copies the Python package into ./python so the published plugin is self-contained.
// Runs automatically on `npm pack` / `npm publish` (prepack); `npm run build` runs it too.
//
// Works in both layouts:
//   workspace:  <workspace>/healthkit-report-plugin      + <workspace>/healthkit-report/src
//   repo:       <repo>/integrations/dsh/plugin           + <repo>/src
import { cpSync, rmSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const candidates = [
  process.env.HEALTHKIT_SRC,
  join(root, "..", "healthkit-report", "src", "healthkit_report"),
  join(root, "..", "..", "..", "src", "healthkit_report"),
].filter(Boolean);

const target = join(root, "python", "healthkit_report");
const source = candidates.find((path) => existsSync(join(path, "__init__.py")));
if (!source) {
  // Standalone plugin repo: python/ is committed, so packing works without the source tree.
  if (existsSync(join(target, "__init__.py"))) {
    console.log("[copy-python] using the committed python/ copy");
    process.exit(0);
  }
  console.error("[copy-python] cannot find healthkit_report source. Tried:");
  for (const path of candidates) console.error(`  - ${path}`);
  console.error("Set HEALTHKIT_SRC=/path/to/src/healthkit_report and retry.");
  process.exit(1);
}

rmSync(join(root, "python"), { recursive: true, force: true });
cpSync(source, target, { recursive: true, filter: (path) => !path.includes("__pycache__") });
console.log(`[copy-python] ${source} -> ${target}`);
