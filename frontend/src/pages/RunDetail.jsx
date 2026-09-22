import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Terminal, FileText, ExternalLink, AlertTriangle } from "lucide-react";
import api from "@/lib/api";
import { Layout, PageHeader } from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { DiffViewer } from "@/components/DiffViewer";
import { cn } from "@/lib/utils";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "different", label: "Different" },
  { key: "identical", label: "Identical" },
  { key: "only-node1", label: "Node 1 Only" },
  { key: "only-node2", label: "Node 2 Only" },
];

function fmt(ts) {
  if (!ts) return "—";
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

export default function RunDetail() {
  const { id } = useParams();
  const [run, setRun] = useState(null);
  const [incident, setIncident] = useState(null);
  const [filter, setFilter] = useState("all");
  const [openFile, setOpenFile] = useState(null);

  useEffect(() => {
    api.get(`/runs/${id}`).then((r) => {
      setRun(r.data);
      const diff = r.data.files?.find((f) => f.status === "different");
      if (diff) setOpenFile(diff.path);
      if (r.data.incident_id) {
        api.get("/incidents").then((res) => {
          setIncident(res.data.find((i) => i.id === r.data.incident_id));
        });
      }
    });
  }, [id]);

  if (!run) {
    return <Layout><PageHeader title="Run" /><div className="p-8 text-slate-500 text-sm">Loading…</div></Layout>;
  }

  const files = (run.files || []).filter((f) => filter === "all" || f.status === filter);
  const s = run.summary;

  return (
    <Layout>
      <PageHeader title={run.node_pair_name} subtitle={`${run.business_name} · ${fmt(run.started_at)}`}>
        <StatusBadge status={run.status} pulse={run.status === "drift"} />
      </PageHeader>

      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-6">
        <Link to="/runs" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 mb-5">
          <ArrowLeft className="h-4 w-4" /> Back to runs
        </Link>

        {run.error && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 mb-5 text-sm text-rose-300" data-testid="run-error">
            <span className="font-mono">SSH/Compare error:</span> {run.error}
          </div>
        )}

        {incident && (
          <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-4 mb-5 fade-up" data-testid="incident-banner">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-cyan-400 mt-0.5" />
              <div className="flex-1">
                <div className="text-sm text-slate-100 font-medium">Freshdesk incident raised <span className="text-[10px] font-mono uppercase bg-slate-700/60 rounded px-1.5 py-0.5 ml-1 text-slate-300">MOCKED</span></div>
                <div className="text-xs text-slate-400 mt-1">{incident.subject}</div>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs font-mono text-cyan-400">{incident.freshdesk_ticket_id}</span>
                  <a href={incident.freshdesk_url} target="_blank" rel="noreferrer" className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1">
                    Open ticket <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        )}

        {s && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
            <SummaryChip label="Total" value={s.total} cls="text-slate-200" />
            <SummaryChip label="Identical" value={s.identical} cls="text-emerald-400" />
            <SummaryChip label="Different" value={s.different} cls="text-red-400" />
            <SummaryChip label="Node 1 Only" value={s.only_node1} cls="text-amber-400" />
            <SummaryChip label="Node 2 Only" value={s.only_node2} cls="text-violet-400" />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* File list */}
          <div className="lg:col-span-1 space-y-3">
            <div className="flex flex-wrap gap-1.5">
              {FILTERS.map((f) => (
                <button key={f.key} data-testid={`filter-${f.key}`} onClick={() => setFilter(f.key)}
                  className={cn("text-xs font-mono px-2.5 py-1 rounded-md border transition-colors",
                    filter === f.key ? "bg-sky-500/15 border-sky-500/40 text-sky-300" : "border-slate-700 text-slate-400 hover:text-slate-200")}>
                  {f.label}
                </button>
              ))}
            </div>
            <div className="rounded-xl border border-slate-800 bg-[#111827] overflow-hidden max-h-[520px] overflow-y-auto" data-testid="file-list">
              {files.length === 0 && <div className="p-6 text-center text-sm text-slate-500">No files in this category.</div>}
              {files.map((f) => (
                <button key={f.path} data-testid={`file-item-${f.path}`} onClick={() => setOpenFile(f.path)}
                  className={cn("w-full text-left px-4 py-2.5 border-b border-slate-800 flex items-center gap-2 hover:bg-slate-800/40 transition-colors",
                    openFile === f.path && "bg-slate-800/60")}>
                  <FileText className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                  <span className="text-xs font-mono text-slate-300 truncate flex-1">{f.path}</span>
                  <StatusBadge status={f.status} />
                </button>
              ))}
            </div>
          </div>

          {/* Diff / logs */}
          <div className="lg:col-span-2 space-y-4">
            {openFile ? (
              <div>
                <div className="text-xs font-mono text-slate-400 mb-2 flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5" /> {openFile}
                </div>
                <DiffViewer diff={run.files.find((f) => f.path === openFile)?.diff} />
              </div>
            ) : (
              <div className="rounded-xl border border-slate-800 bg-[#111827] p-8 text-center text-sm text-slate-500">
                Select a file to view its diff.
              </div>
            )}

            {run.logs?.length > 0 && (
              <div className="rounded-xl border border-slate-800 bg-[#0B0F19] overflow-hidden" data-testid="execution-logs">
                <div className="px-4 py-2.5 border-b border-slate-800 flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-slate-400">
                  <Terminal className="h-3.5 w-3.5" /> Execution Log
                </div>
                <pre className="p-4 text-xs font-mono text-slate-400 leading-relaxed whitespace-pre-wrap">
                  {run.logs.map((l, i) => <div key={i}><span className="text-slate-600">$</span> {l}</div>)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}

function SummaryChip({ label, value, cls }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-[#111827] px-4 py-3">
      <div className={cn("font-display text-2xl font-bold", cls)}>{value}</div>
      <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mt-0.5">{label}</div>
    </div>
  );
}
