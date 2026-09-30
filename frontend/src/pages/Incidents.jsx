import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ExternalLink, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { Layout, PageHeader } from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

const STATUSES = ["open", "resolved", "closed"];

function fmt(ts) {
  if (!ts) return "—";
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

export default function Incidents() {
  const [incidents, setIncidents] = useState([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    const q = filter === "all" ? "" : `?status=${filter}`;
    api.get(`/incidents${q}`).then((r) => setIncidents(r.data)).finally(() => setLoading(false));
  };
  useEffect(load, [filter]);

  const changeStatus = async (id, status) => {
    await api.put(`/incidents/${id}/status?status=${status}`);
    toast.success(`Incident marked ${status}`);
    load();
  };

  return (
    <Layout>
      <PageHeader title="Incidents" subtitle="Freshdesk tickets raised on config drift (mocked)">
        <div className="flex gap-1.5">
          {["all", ...STATUSES].map((s) => (
            <button key={s} data-testid={`incident-filter-${s}`} onClick={() => setFilter(s)}
              className={cn("text-xs font-mono px-3 py-1.5 rounded-md border transition-colors capitalize",
                filter === s ? "bg-sky-500/15 border-sky-500/40 text-sky-300" : "border-slate-700 text-slate-400 hover:text-slate-200")}>
              {s}
            </button>
          ))}
        </div>
      </PageHeader>

      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-6">
        {loading ? (
          <div className="text-slate-500 text-sm">Loading…</div>
        ) : incidents.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-700 bg-[#111827]/50 p-12 text-center" data-testid="incidents-empty">
            <AlertTriangle className="h-10 w-10 text-slate-600 mx-auto mb-3" />
            <div className="text-slate-300 font-medium">No incidents</div>
            <p className="text-sm text-slate-500 mt-1">Incidents are auto-created when a comparison detects drift.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {incidents.map((i) => (
              <Collapsible key={i.id} data-testid={`incident-${i.id}`} className="rounded-xl border border-slate-800 bg-[#111827] overflow-hidden fade-up">
                <div className="flex items-center gap-4 px-5 py-4">
                  <div className="h-9 w-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0">
                    <AlertTriangle className="h-4.5 w-4.5 text-cyan-400" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-cyan-400">{i.freshdesk_ticket_id}</span>
                      <StatusBadge status={i.status} />
                      {i.mocked && <span className="text-[10px] font-mono uppercase bg-slate-700/60 rounded px-1.5 py-0.5 text-slate-400">MOCKED</span>}
                    </div>
                    <div className="text-sm text-slate-200 mt-1 truncate">{i.subject}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">{i.business_name} · {fmt(i.created_at)}</div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Select value={i.status} onValueChange={(v) => changeStatus(i.id, v)}>
                      <SelectTrigger data-testid={`incident-status-${i.id}`} className="w-32 h-8 bg-[#0B0F19] border-slate-700 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-[#111827] border-slate-800 text-slate-200">
                        {STATUSES.map((s) => <SelectItem key={s} value={s} className="capitalize text-xs">{s}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <CollapsibleTrigger asChild>
                      <button data-testid={`incident-expand-${i.id}`} className="p-1.5 text-slate-500 hover:text-slate-200">
                        <ChevronDown className="h-4 w-4" />
                      </button>
                    </CollapsibleTrigger>
                  </div>
                </div>
                <CollapsibleContent>
                  <div className="px-5 pb-5 border-t border-slate-800 pt-4">
                    <pre className="text-xs font-mono text-slate-400 whitespace-pre-wrap bg-[#0B0F19] rounded-lg p-4 border border-slate-800">{i.description}</pre>
                    <div className="flex items-center gap-4 mt-3">
                      <a href={i.freshdesk_url} target="_blank" rel="noreferrer" className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1">
                        Open in Freshdesk <ExternalLink className="h-3 w-3" />
                      </a>
                      <Link to={`/runs/${i.run_id}`} className="text-xs text-sky-400 hover:text-sky-300">View comparison run</Link>
                    </div>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
