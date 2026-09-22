import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Building2, Server, AlertTriangle, GitCompareArrows, ShieldCheck, Activity, ArrowRight, Sparkles } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { Layout, PageHeader } from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";

function StatCard({ icon: Icon, label, value, accent, testid }) {
  return (
    <div data-testid={testid} className="rounded-xl border border-slate-800 bg-[#111827] p-5 fade-up">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono uppercase tracking-wider text-slate-500">{label}</span>
        <Icon className={`h-4 w-4 ${accent}`} />
      </div>
      <div className="mt-3 font-display text-3xl font-bold text-slate-100">{value}</div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [seeding, setSeeding] = useState(false);

  const load = () => api.get("/dashboard/stats").then((r) => setStats(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const loadDemo = async () => {
    setSeeding(true);
    try {
      await api.post("/demo/seed");
      toast.success("Demo data loaded", { description: "Sample business, node pair, drift run & incident created." });
      await load();
    } catch {
      toast.error("Failed to load demo data");
    } finally {
      setSeeding(false);
    }
  };

  const isEmpty = stats && stats.total_businesses === 0 && stats.total_runs === 0;

  return (
    <Layout>
      <PageHeader title="Operations Dashboard" subtitle="Config drift posture across your fleet">
        {isEmpty && (
          <Button data-testid="load-demo-btn" onClick={loadDemo} disabled={seeding} className="bg-indigo-500 hover:bg-indigo-400 text-white">
            <Sparkles className="h-4 w-4 mr-1" /> {seeding ? "Loading…" : "Load Demo Data"}
          </Button>
        )}
      </PageHeader>
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-6">
        {!stats ? (
          <div className="text-slate-500 text-sm">Loading…</div>
        ) : (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <StatCard testid="stat-businesses" icon={Building2} label="Businesses" value={stats.total_businesses} accent="text-sky-400" />
              <StatCard testid="stat-nodepairs" icon={Server} label="Node Pairs" value={stats.total_node_pairs} accent="text-indigo-400" />
              <StatCard testid="stat-drift" icon={AlertTriangle} label="Drifted Pairs" value={stats.drifted_pairs} accent="text-red-400" />
              <StatCard testid="stat-incidents" icon={GitCompareArrows} label="Open Incidents" value={stats.open_incidents} accent="text-cyan-400" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
              <div className="rounded-xl border border-slate-800 bg-[#111827] p-5 flex items-center gap-4">
                <ShieldCheck className="h-8 w-8 text-emerald-400" />
                <div>
                  <div className="text-2xl font-display font-bold text-slate-100">{stats.synced_pairs}</div>
                  <div className="text-xs text-slate-500">Synced node pairs</div>
                </div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-[#111827] p-5 flex items-center gap-4">
                <Activity className="h-8 w-8 text-sky-400" />
                <div>
                  <div className="text-2xl font-display font-bold text-slate-100">{stats.total_runs}</div>
                  <div className="text-xs text-slate-500">Total comparison runs</div>
                </div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-[#111827] p-5 flex items-center gap-4">
                <AlertTriangle className="h-8 w-8 text-cyan-400" />
                <div>
                  <div className="text-2xl font-display font-bold text-slate-100">{stats.total_incidents}</div>
                  <div className="text-xs text-slate-500">Total Freshdesk incidents</div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="rounded-xl border border-slate-800 bg-[#111827] overflow-hidden">
                <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between">
                  <h2 className="font-display font-semibold text-slate-200 text-sm">Recent Comparison Runs</h2>
                  <Link to="/runs" className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1" data-testid="view-all-runs">
                    View all <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
                <div className="divide-y divide-slate-800">
                  {stats.recent_runs.length === 0 && (
                    <div className="px-5 py-8 text-center text-sm text-slate-500">No runs yet.</div>
                  )}
                  {stats.recent_runs.map((r) => (
                    <Link key={r.id} to={`/runs/${r.id}`} className="flex items-center justify-between px-5 py-3 hover:bg-slate-800/40 transition-colors">
                      <div className="min-w-0">
                        <div className="text-sm text-slate-200 truncate">{r.node_pair_name}</div>
                        <div className="text-[11px] text-slate-500 font-mono">{r.business_name} · {r.triggered_by}</div>
                      </div>
                      <StatusBadge status={r.status} />
                    </Link>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-[#111827] overflow-hidden">
                <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between">
                  <h2 className="font-display font-semibold text-slate-200 text-sm">Recent Incidents</h2>
                  <Link to="/incidents" className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1" data-testid="view-all-incidents">
                    View all <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
                <div className="divide-y divide-slate-800">
                  {stats.recent_incidents.length === 0 && (
                    <div className="px-5 py-8 text-center text-sm text-slate-500">No incidents raised.</div>
                  )}
                  {stats.recent_incidents.map((i) => (
                    <div key={i.id} className="px-5 py-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-mono text-cyan-400">{i.freshdesk_ticket_id}</span>
                        <StatusBadge status={i.status} />
                      </div>
                      <div className="text-sm text-slate-300 mt-1 truncate">{i.subject}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
