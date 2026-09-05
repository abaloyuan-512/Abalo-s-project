import { spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, renameSync } from "node:fs";
import { resolve } from "node:path";

// vinext writes to dist. Preserve any previous portable artifact rather than
// recursively deleting a computed location.
const result = spawnSync(process.execPath, ["node_modules/vinext/dist/cli.js", "build"], {
  stdio: "inherit",
  env: { ...process.env, GUANXIANG_RUNTIME: "portable" },
});
if (result.status !== 0) process.exit(result.status ?? 1);
const output = resolve("dist-portable");
mkdirSync(resolve("work"), { recursive: true });
if (existsSync(output)) renameSync(output, resolve(`work/portable-build-${Date.now()}`));
cpSync(resolve("dist"), output, { recursive: true });
console.log("Portable Node.js artifact: dist-portable");
