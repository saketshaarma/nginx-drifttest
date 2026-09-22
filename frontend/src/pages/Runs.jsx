import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { GitCompareArrows, ArrowRight } from "lucide-react";
import api from "@/lib/api";
import { Layout, PageHeader } from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";

function fmt(ts) {
  if (!ts) return "—";
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

export default function Runs() {
  const [params] = useSearchParams();
  const mappingId = params.get("mapping_id");
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const q = mappingId ? `?mapping_id=${mappingId}` : "";
    api.get(`/runs${q}`).then((r) => setRuns(r.data)).finally(() => setLoading(false));
  }, [mappingId]);

  return (
    <Layout>
      <PageHeader title="Comparison Runs" subtitle={mappingId ? "Filtered by mapping" : "Full comparison history"} />
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-6">
        {loading ? (
          <div className="text-slate-500 text-sm">Loading…</div>
        ) : runs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-700 bg-[#111827]/50 p-12 text-center" data-testid="runs-empty">
            <GitCompareArrows className="h-10 w-10 text-slate-600 mx-auto mb-3" />
            <div className="text-slate-300 font-medium">No comparison runs yet</div>
            <p className="text-sm text-slate-500 mt-1">Trigger a comparison from a node pair to see results here.</p>
          </div>
        ) : (
          <div className="rounded-xl border border-slate-800 bg-[#111827] overflow-hidden">
            <div className="grid grid-cols-12 px-5 py-3 border-b border-slate-800 text-[11px] font-mono uppercase tracking-wider text-slate-500">
              <div className="col-span-4">Mapping</div>
              <div className="col-span-2">Status</div>
              <div className="col-span-2">Trigger</div>
              <div className="col-span-3">Started</div>
              <div className="col-span-1"></div>
            </div>
            <div className="divide-y divide-slate-800">
              {runs.map((r) => (
                <Link key={r.id} to={`/runs/${r.id}`} data-testid={`run-row-${r.id}`} className="grid grid-cols-12 px-5 py-3.5 items-center hover:bg-slate-800/40 transition-colors">
                  <div className="col-span-4 min-w-0">
                    <div className="text-sm text-slate-200 truncate">{r.mapping_name}</div>
                    <div className="text-[11px] text-slate-500">{r.business_name}{r.summary ? ` · ${r.summary.pairs_drifted}/${r.summary.pairs_total} drifted` : ""}</div>
                  </div>
                  <div className="col-span-2"><StatusBadge status={r.status} /></div>
                  <div className="col-span-2 text-xs font-mono text-slate-400">{r.triggered_by}</div>
                  <div className="col-span-3 text-xs text-slate-400">{fmt(r.started_at)}</div>
                  <div className="col-span-1 flex justify-end"><ArrowRight className="h-4 w-4 text-slate-600" /></div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
