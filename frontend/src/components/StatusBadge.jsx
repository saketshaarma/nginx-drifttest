import { cn } from "@/lib/utils";

const MAP = {
  identical: { label: "Identical", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" },
  synced: { label: "Synced", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" },
  different: { label: "Drift", cls: "text-red-400 bg-red-500/10 border-red-500/30" },
  drift: { label: "Config Drift", cls: "text-red-400 bg-red-500/10 border-red-500/30" },
  "only-node1": { label: "Node 1 Only", cls: "text-amber-400 bg-amber-500/10 border-amber-500/30" },
  "only-node2": { label: "Node 2 Only", cls: "text-violet-400 bg-violet-500/10 border-violet-500/30" },
  running: { label: "Running", cls: "text-sky-400 bg-sky-500/10 border-sky-500/30" },
  failed: { label: "Failed", cls: "text-rose-400 bg-rose-500/10 border-rose-500/30" },
  open: { label: "Open", cls: "text-cyan-400 bg-cyan-500/10 border-cyan-500/30" },
  resolved: { label: "Resolved", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" },
  closed: { label: "Closed", cls: "text-slate-400 bg-slate-500/10 border-slate-500/30" },
  never: { label: "Never Run", cls: "text-slate-400 bg-slate-500/10 border-slate-500/30" },
};

export function StatusBadge({ status, className, pulse }) {
  const conf = MAP[status] || MAP.never;
  return (
    <span
      data-testid={`status-badge-${status || "never"}`}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-mono font-medium",
        conf.cls,
        className
      )}
    >
      {pulse && <span className={cn("h-1.5 w-1.5 rounded-full bg-current", pulse && "pulse-dot")} />}
      {conf.label}
    </span>
  );
}
