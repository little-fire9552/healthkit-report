import { execFile } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { delimiter, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { defineTool } from "@deepseek-ai/dsh-tools";

/**
 * DSH Host plugin for healthkit-report.
 *
 * Registers one agent tool, `healthkit_report`, that shells out to the Python
 * package (`python -m healthkit_report <subcommand>`) and returns its output.
 */

/** Cordis plugin name. */
const name = "tool-healthkit-report";

/** Services used by the tool. */
const inject = ["tools"];

const ACTIONS = new Set(["parse", "analyze", "report", "all"]);

function buildArgs(args) {
  const action = String(args.action || "").toLowerCase();
  if (!ACTIONS.has(action)) {
    throw new Error(
      `unknown action "${args.action}"; expected one of parse, analyze, report, all`,
    );
  }
  const target = action === "parse" || action === "all" ? args.export : args.dataset;
  if (!target) {
    throw new Error(
      action === "parse" || action === "all"
        ? "`export` is required: absolute path to export.xml or the unzipped apple_health_export directory"
        : "`dataset` is required: absolute path to the dataset.json produced by parse",
    );
  }
  const argv = ["-m", "healthkit_report", action, target];
  const out = args.out || (action === "parse" ? "dataset.json"
    : action === "analyze" ? "findings.json" : "out");
  argv.push("-o", out);
  if (args.since) argv.push("--since", args.since);
  if (args.until) argv.push("--until", args.until);
  if (action === "report" || action === "all") {
    if (args.patient_name) argv.push("--name", args.patient_name);
    if (args.formats) argv.push("--formats", args.formats);
  }
  if (args.priority) argv.push("--priority", ...String(args.priority).split(","));
  return { action, argv };
}

/**
 * Prefer the Python that ships with DeepSeek Harness: it is the one users can
 * install python-docx into without fighting macOS's system Python.
 */
function defaultPython() {
  const home = process.env.DSH_HOME;
  if (home) {
    try {
      const root = join(home, "dsh-runtimes");
      for (const entry of readdirSync(root)) {
        const candidate = join(root, entry, "dependencies", "python", "bin", "python3");
        if (existsSync(candidate)) return candidate;
      }
    } catch {
      // fall through to PATH
    }
  }
  return "python3";
}

/**
 * The published package bundles the Python source under ./python so users only
 * need python-docx / XlsxWriter; prepend it to PYTHONPATH when present.
 */
function pythonPath() {
  const here = dirname(fileURLToPath(import.meta.url));
  const bundled = join(here, "python");
  const parts = [process.env.PYTHONPATH].filter(Boolean);
  if (existsSync(bundled)) parts.unshift(bundled);
  return parts.join(delimiter);
}

function runPython(command, argv, { cwd, timeoutMs, signal }) {
  return new Promise((resolve, reject) => {
    const child = execFile(
      command,
      argv,
      {
        cwd: cwd || process.cwd(),
        timeout: timeoutMs,
        maxBuffer: 32 * 1024 * 1024,
        signal,
        env: { ...process.env, PYTHONPATH: pythonPath() },
      },
      (error, stdout, stderr) => {
        if (error && error.killed) {
          reject(new Error(`healthkit-report timed out after ${timeoutMs} ms`));
          return;
        }
        resolve({
          exitCode: error ? (typeof error.code === "number" ? error.code : 1) : 0,
          stdout: stdout ?? "",
          stderr: stderr ?? "",
        });
      },
    );
    // The CLI never reads stdin; closing it prevents a child waiting on a TTY.
    child.stdin?.end();
  });
}

/** The agent-facing tool definition. */
function healthkitTool() {
  return defineTool({
    name: "healthkit_report",
    description:
      "Analyse an Apple Health export (export.xml from 健康 App → 导出所有健康数据) and build reports. "
      + "De-duplicates records written by several devices (iPhone + Apple Watch), computes 34 metrics, "
      + "and writes DOCX/XLSX/HTML. "
      + "action=all is the usual entry point: it parses, analyses and writes reports in one call. "
      + "action=parse writes dataset.json, action=analyze writes findings.json, action=report renders from an existing dataset.json. "
      + "Never sum the raw XML yourself: it double counts overlapping device records.",
    timeoutMs: 30 * 60 * 1000,
    parameters: {
      action: {
        type: "string",
        required: true,
        description: "parse | analyze | report | all. Use 'all' unless you need to reuse an intermediate JSON.",
      },
      export: {
        type: "string",
        description: "Absolute path to export.xml or the unzipped apple_health_export directory. Required for parse/all.",
      },
      dataset: {
        type: "string",
        description: "Absolute path to a dataset.json produced by action=parse. Required for analyze/report.",
      },
      out: {
        type: "string",
        description: "Output path: dataset/findings JSON file for parse/analyze, or the report directory for report/all. Defaults to dataset.json / findings.json / out.",
      },
      patient_name: {
        type: "string",
        description: "Name printed on the report cover. Optional.",
      },
      formats: {
        type: "string",
        description: "Comma separated subset of docx,xlsx,html. Defaults to all three.",
      },
      since: { type: "string", description: "Inclusive start date YYYY-MM-DD. Optional." },
      until: { type: "string", description: "Inclusive end date YYYY-MM-DD. Optional." },
      priority: {
        type: "string",
        description: "Comma separated device precedence, best first. Defaults to Watch,iPhone,iPad,Mac,iPod.",
      },
      python: {
        type: "string",
        description: "Python executable that has healthkit-report installed. Defaults to $HEALTHKIT_PYTHON or python3.",
      },
      cwd: { type: "string", description: "Working directory for relative out/export paths. Optional." },
    },
    output: {
      schema: {
        type: "object",
        additionalProperties: false,
        properties: {
          ok: { type: "boolean", required: true, description: "True when the command exited 0." },
          action: { type: "string", required: true, description: "The subcommand that ran." },
          command: { type: "string", required: true, description: "Human readable command line." },
          exit_code: { type: "integer", required: true, description: "Process exit code." },
          stdout: { type: "string", required: true, description: "Standard output (may be empty)." },
          stderr: { type: "string", required: true, description: "Standard error (progress and errors)." },
        },
      },
      render: (_args, value) => {
        const text = [
          `${value.ok ? "ok" : "failed"} · ${value.action} · exit ${value.exit_code}`,
          value.stdout.trim(),
          value.stderr.trim() ? `[stderr]\n${value.stderr.trim()}` : "",
        ].filter(Boolean).join("\n");
        return [{ type: "text", text }];
      },
    },
    async execute(args, exec) {
      const { action, argv } = buildArgs(args);
      const python = args.python || process.env.HEALTHKIT_PYTHON || defaultPython();
      const result = await runPython(python, argv, {
        cwd: args.cwd,
        timeoutMs: 30 * 60 * 1000,
        signal: exec?.signal,
      });
      let stderr = result.stderr;
      if (result.exitCode !== 0) {
        if (stderr.includes("No module named 'healthkit_report'")) {
          stderr += `\n[hint] 该解释器没有安装本包：${python} -m pip install -e <healthkit-report 源码目录>，`
            + "或用 python 参数指定已安装的解释器。";
        } else if (stderr.includes("No module named 'docx'")) {
          stderr += `\n[hint] 缺少 python-docx：${python} -m pip install python-docx XlsxWriter。`;
        }
      }
      return {
        ok: result.exitCode === 0,
        action,
        command: [python, ...argv].join(" "),
        exit_code: result.exitCode,
        stdout: result.stdout,
        stderr,
      };
    },
    isConcurrencySafe: () => false,
  });
}

/**
 * Register the healthkit-report tool.
 * @param ctx - context providing the tool registry.
 */
function apply(ctx) {
  ctx.tools.register(healthkitTool());
}

export { apply, inject, name };
