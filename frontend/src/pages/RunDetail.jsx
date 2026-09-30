import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Terminal, FileText, ExternalLink, AlertTriangle, ArrowRightLeft } from "lucide-react";
import api from "@/lib/api";
import { Layout, PageHeader } from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { DiffViewer } from "@/components/DiffViewer";
import { cn } from "@/lib/utils";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "different", label: "Different" },
  { key: "identical", label: "Identical" },
  { key: "only-dc", label: "DC Only" },
  { key: "only-dr", label: "DR Only" },
];

function fmt(ts) {
  if (!ts) return "—";
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

export default function RunDetail() {
  const { id } = useParams();
  const [run, setRun] = useState(null);
  const [incident, setIncident] = useState(null);
  const [activePair, setActivePair] = useState(0);
  const [filter, setFilter] = useState("all");
  const [openFile, setOpenFile] = useState(null);

  useEffect(() => {
    let timer;
    let cancelled = false;

    const fetchRun = async (isPoll) => {
      const r = await api.get(`/runs/${id}`);
      if (cancelled) return;
      setRun(r.data);
      if (!isPoll) {
        const pairs = r.data.pairs || [];
        const driftIdx = pairs.findIndex((p) => p.status === "drift");
        const idx = driftIdx >= 0 ? driftIdx : 0;
        setActivePair(idx);
        const diff = pairs[idx]?.files?.find((f) => f.status === "different");
        if (diff) setOpenFile(diff.path);
      }
      if (r.data.incident_id) {
        api.get("/incidents").then((res) => setIncident(res.data.find((i) => i.id === r.data.incident_id)));
      }
      if (r.data.status === "running") {
        timer = setTimeout(() => fetchRun(true), 2500);
      } else if (isPoll) {
        // just completed via poll: pick a good default pair/file once
        const pairs = r.data.pairs || [];
        const driftIdx = pairs.findIndex((p) => p.status === "drift");
        const idx = driftIdx >= 0 ? driftIdx : 0;
        setActivePair(idx);
        const diff = pairs[idx]?.files?.find((f) => f.status === "different");
        setOpenFile(diff ? diff.path : null);
      }
    };

    fetchRun(false);
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, [id]);

  if (!run) {
    return <Layout><PageHeader title="Run" /><div className="p-8 text-slate-500 text-sm">Loading…</div></Layout>;
  }

  const pairs = run.pairs || [];
  const pair = pairs[activePair];
  const files = (pair?.files || []).filter((f) => filter === "all" || f.status === filter);
  const s = run.summary;

  const selectPair = (idx) => {
    setActivePair(idx);
    setFilter("all");
    const diff = pairs[idx]?.files?.find((f) => f.status === "different");
    setOpenFile(diff ? diff.path : null);
  };

  return (
    <Layout>
      <PageHeader title={run.mapping_name} subtitle={`${run.business_name} · ${fmt(run.started_at)}`}>
        <StatusBadge status={run.status} pulse={run.status === "drift"} />
      </PageHeader>

      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-6">
        <Link to="/runs" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 mb-5">
          <ArrowLeft className="h-4 w-4" /> Back to runs
        </Link>

        {run.status === "running" && (
          <div className="rounded-xl border border-sky-500/30 bg-sky-500/10 p-4 mb-5 flex items-center gap-3" data-testid="run-running">
            <span className="h-2 w-2 rounded-full bg-sky-400 pulse-dot" />
            <span className="text-sm text-sky-300 font-mono">Comparison in progress — connecting via SSH and diffing config files…</span>
          </div>
        )}

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
                <div className="text-sm text-slate-100 font-medium">Freshdesk incident raised {incident.mocked && <span className="text-[10px] font-mono uppercase bg-slate-700/60 rounded px-1.5 py-0.5 ml-1 text-slate-300">MOCKED</span>}</div>
                <div className="text-xs text-slate-400 mt-1">{incident.subject}</div>
                {incident.mocked && incident.freshdesk_error && (
                  <div className="text-[11px] text-amber-400/90 mt-1">Freshdesk not created ({incident.freshdesk_error}); showing a mock ticket.</div>
                )}
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
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
            <SummaryChip label="Pairs" value={`${s.pairs_drifted}/${s.pairs_total}`} cls="text-slate-200" hint="drifted" />
            <SummaryChip label="Files" value={s.total} cls="text-slate-200" />
            <SummaryChip label="Identical" value={s.identical} cls="text-emerald-400" />
            <SummaryChip label="Different" value={s.different} cls="text-red-400" />
            <SummaryChip label="DC Only" value={s.only_dc} cls="text-amber-400" />
            <SummaryChip label="DR Only" value={s.only_dr} cls="text-violet-400" />
          </div>
        )}

        {/* Pair selector */}
        {pairs.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4" data-testid="pair-selector">
            {pairs.map((p, idx) => (
              <button key={p.pair_id} data-testid={`pair-tab-${idx}`} onClick={() => selectPair(idx)}
                className={cn("flex items-center gap-2 rounded-lg border px-3 py-2 transition-colors",
                  activePair === idx ? "bg-slate-800/70 border-slate-600" : "border-slate-800 bg-[#111827] hover:border-slate-700")}>
                <span className="text-xs font-mono text-amber-400/90">{p.dc_node}</span>
                <ArrowRightLeft className="h-3 w-3 text-slate-600" />
                <span className="text-xs font-mono text-violet-400/90">{p.dr_node}</span>
                <StatusBadge status={p.status} />
              </button>
            ))}
          </div>
        )}

        {pair?.error && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 mb-4 text-sm text-rose-300" data-testid="pair-error">
            <span className="font-mono">Pair error ({pair.dc_node} ↔ {pair.dr_node}):</span> {pair.error}
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
                <DiffViewer diff={pair?.files.find((f) => f.path === openFile)?.diff} />
              </div>
            ) : (
              <div className="rounded-xl border border-slate-800 bg-[#111827] p-8 text-center text-sm text-slate-500">
                Select a file to view its diff.
              </div>
            )}

            {pair?.logs?.length > 0 && (
              <div className="rounded-xl border border-slate-800 bg-[#0B0F19] overflow-hidden" data-testid="execution-logs">
                <div className="px-4 py-2.5 border-b border-slate-800 flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-slate-400">
                  <Terminal className="h-3.5 w-3.5" /> Execution Log — {pair.dc_node} ↔ {pair.dr_node}
                </div>
                <pre className="p-4 text-xs font-mono text-slate-400 leading-relaxed whitespace-pre-wrap">
                  {pair.logs.map((l, i) => <div key={i}><span className="text-slate-600">$</span> {l}</div>)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}

function SummaryChip({ label, value, cls, hint }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-[#111827] px-4 py-3">
      <div className={cn("font-display text-2xl font-bold", cls)}>{value}</div>
      <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mt-0.5">{label}{hint ? ` · ${hint}` : ""}</div>
    </div>
  );
}
