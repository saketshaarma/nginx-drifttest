import { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  Plus, Server, Play, Pencil, Trash2, Clock, ArrowLeft, Loader2, FolderTree, Network, History,
} from "lucide-react";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { Layout, PageHeader } from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const EMPTY = {
  name: "", node1: "", node2: "", port1: 22, port2: 22, folder: "/etc/nginx",
  ssh_username: "", ssh_password: "", schedule_enabled: false, schedule_interval_minutes: 60,
};

function NodePairDialog({ open, onOpenChange, businessId, editing, onSaved }) {
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (editing) {
      setForm({ ...EMPTY, ...editing, ssh_password: "" });
    } else {
      setForm(EMPTY);
    }
  }, [editing, open]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      if (editing) {
        const payload = { ...form };
        if (!payload.ssh_password) delete payload.ssh_password;
        await api.put(`/node-pairs/${editing.id}`, payload);
        toast.success("Node pair updated");
      } else {
        await api.post("/node-pairs", { ...form, business_id: businessId });
        toast.success("Node pair created");
      }
      onSaved();
      onOpenChange(false);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#111827] border-slate-800 text-slate-200 max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-display">{editing ? "Edit Node Pair" : "New Node Pair"}</DialogTitle>
          <DialogDescription className="text-slate-500 text-sm">Map two nginx nodes and the config folder to compare over SSH.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <Field label="Mapping Name">
            <Input data-testid="np-name-input" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Edge LB Pair" className="bg-[#0B0F19] border-slate-700" />
          </Field>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2"><Field label="Node 1 Host">
              <Input data-testid="np-node1-input" value={form.node1} onChange={(e) => set("node1", e.target.value)} placeholder="10.0.0.1" className="bg-[#0B0F19] border-slate-700 font-mono" />
            </Field></div>
            <Field label="Port 1">
              <Input data-testid="np-port1-input" type="number" value={form.port1} onChange={(e) => set("port1", parseInt(e.target.value) || 22)} className="bg-[#0B0F19] border-slate-700 font-mono" />
            </Field>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2"><Field label="Node 2 Host">
              <Input data-testid="np-node2-input" value={form.node2} onChange={(e) => set("node2", e.target.value)} placeholder="10.0.0.2" className="bg-[#0B0F19] border-slate-700 font-mono" />
            </Field></div>
            <Field label="Port 2">
              <Input data-testid="np-port2-input" type="number" value={form.port2} onChange={(e) => set("port2", parseInt(e.target.value) || 22)} className="bg-[#0B0F19] border-slate-700 font-mono" />
            </Field>
          </div>
          <Field label="Config Folder">
            <Input data-testid="np-folder-input" value={form.folder} onChange={(e) => set("folder", e.target.value)} placeholder="/etc/nginx" className="bg-[#0B0F19] border-slate-700 font-mono" />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="SSH Username">
              <Input data-testid="np-user-input" value={form.ssh_username} onChange={(e) => set("ssh_username", e.target.value)} placeholder="root" className="bg-[#0B0F19] border-slate-700 font-mono" />
            </Field>
            <Field label={editing ? "SSH Password (blank = keep)" : "SSH Password"}>
              <Input data-testid="np-pass-input" type="password" value={form.ssh_password} onChange={(e) => set("ssh_password", e.target.value)} placeholder="••••••••" className="bg-[#0B0F19] border-slate-700 font-mono" />
            </Field>
          </div>
          <div className="rounded-lg border border-slate-800 bg-[#0B0F19] p-3 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <Clock className="h-4 w-4 text-sky-400" /> Scheduled comparison
              </div>
              <Switch data-testid="np-schedule-switch" checked={form.schedule_enabled} onCheckedChange={(v) => set("schedule_enabled", v)} />
            </div>
            {form.schedule_enabled && (
              <Field label="Every (minutes)">
                <Input data-testid="np-interval-input" type="number" min={1} value={form.schedule_interval_minutes} onChange={(e) => set("schedule_interval_minutes", parseInt(e.target.value) || 60)} className="bg-[#111827] border-slate-700 font-mono" />
              </Field>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button data-testid="save-np-btn" onClick={save} disabled={saving} className="bg-sky-500 hover:bg-sky-400 text-white">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : editing ? "Save Changes" : "Create Node Pair"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({ label, children }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-mono uppercase tracking-wider text-slate-400">{label}</Label>
      {children}
    </div>
  );
}

export default function BusinessDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [business, setBusiness] = useState(null);
  const [pairs, setPairs] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [runningId, setRunningId] = useState(null);

  const load = useCallback(() => {
    api.get(`/businesses/${id}`).then((r) => setBusiness(r.data)).catch(() => navigate("/businesses"));
    api.get(`/node-pairs?business_id=${id}`).then((r) => setPairs(r.data));
  }, [id, navigate]);

  useEffect(load, [load]);

  const runCompare = async (pairId) => {
    setRunningId(pairId);
    toast.info("Running comparison…", { description: "Connecting via SSH and diffing config files." });
    try {
      const { data } = await api.post(`/node-pairs/${pairId}/compare`);
      if (data.status === "failed") {
        toast.error("Comparison failed", { description: data.error });
      } else if (data.status === "drift") {
        toast.warning("Config drift detected", { description: "A Freshdesk incident was raised." });
      } else {
        toast.success("Configs identical", { description: "No drift detected." });
      }
      load();
      navigate(`/runs/${data.id}`);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    } finally {
      setRunningId(null);
    }
  };

  const remove = async (pairId) => {
    await api.delete(`/node-pairs/${pairId}`);
    toast.success("Node pair deleted");
    load();
  };

  return (
    <Layout>
      <PageHeader title={business?.name || "Business"} subtitle={business?.description}>
        <Button data-testid="new-nodepair-btn" onClick={() => { setEditing(null); setDialogOpen(true); }} className="bg-sky-500 hover:bg-sky-400 text-white">
          <Plus className="h-4 w-4 mr-1" /> New Node Pair
        </Button>
      </PageHeader>

      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-6">
        <Link to="/businesses" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 mb-5">
          <ArrowLeft className="h-4 w-4" /> Back to businesses
        </Link>

        {pairs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-700 bg-[#111827]/50 p-12 text-center" data-testid="nodepairs-empty">
            <Server className="h-10 w-10 text-slate-600 mx-auto mb-3" />
            <div className="text-slate-300 font-medium">No node pairs mapped</div>
            <p className="text-sm text-slate-500 mt-1">Map two nginx nodes to compare their config files.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {pairs.map((p) => (
              <div key={p.id} data-testid={`nodepair-card-${p.id}`} className="rounded-xl border border-slate-800 bg-[#111827] p-5 fade-up">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-display font-semibold text-slate-100 flex items-center gap-2">
                      {p.name}
                      {p.schedule_enabled && (
                        <span className="text-[10px] font-mono text-sky-400 bg-sky-500/10 border border-sky-500/20 rounded px-1.5 py-0.5 flex items-center gap-1">
                          <Clock className="h-2.5 w-2.5" /> {p.schedule_interval_minutes}m
                        </span>
                      )}
                    </h3>
                    <StatusBadge status={p.last_status || "never"} className="mt-2" pulse={p.last_status === "drift"} />
                  </div>
                  <div className="flex items-center gap-1">
                    <button data-testid={`edit-np-${p.id}`} onClick={() => { setEditing(p); setDialogOpen(true); }} className="p-1.5 text-slate-500 hover:text-slate-200 transition-colors">
                      <Pencil className="h-4 w-4" />
                    </button>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <button data-testid={`delete-np-${p.id}`} className="p-1.5 text-slate-500 hover:text-red-400 transition-colors">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </AlertDialogTrigger>
                      <AlertDialogContent className="bg-[#111827] border-slate-800 text-slate-200">
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete {p.name}?</AlertDialogTitle>
                          <AlertDialogDescription className="text-slate-400">This removes the node pair mapping and its schedule.</AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel className="bg-transparent border-slate-700 text-slate-300">Cancel</AlertDialogCancel>
                          <AlertDialogAction data-testid={`confirm-delete-np-${p.id}`} onClick={() => remove(p.id)} className="bg-red-500 hover:bg-red-400 text-white">Delete</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>

                <div className="mt-4 space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-slate-400">
                    <Network className="h-3.5 w-3.5 text-slate-500" />
                    <span className="font-mono text-slate-300">{p.node1}:{p.port1}</span>
                    <span className="text-slate-600">↔</span>
                    <span className="font-mono text-slate-300">{p.node2}:{p.port2}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-400">
                    <FolderTree className="h-3.5 w-3.5 text-slate-500" />
                    <span className="font-mono text-slate-300">{p.folder}</span>
                  </div>
                  {p.last_summary && (
                    <div className="flex items-center gap-3 text-xs font-mono pt-1">
                      <span className="text-emerald-400">{p.last_summary.identical} same</span>
                      <span className="text-red-400">{p.last_summary.different} diff</span>
                      <span className="text-amber-400">{p.last_summary.only_node1} n1</span>
                      <span className="text-violet-400">{p.last_summary.only_node2} n2</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-800">
                  <Button data-testid={`run-compare-${p.id}`} onClick={() => runCompare(p.id)} disabled={runningId === p.id} size="sm" className="bg-sky-500 hover:bg-sky-400 text-white flex-1">
                    {runningId === p.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Play className="h-3.5 w-3.5 mr-1" /> Run Compare</>}
                  </Button>
                  <Link to={`/runs?node_pair_id=${p.id}`} data-testid={`history-np-${p.id}`}>
                    <Button size="sm" variant="outline" className="bg-transparent border-slate-700 text-slate-300 hover:bg-slate-800">
                      <History className="h-3.5 w-3.5 mr-1" /> History
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <NodePairDialog open={dialogOpen} onOpenChange={setDialogOpen} businessId={id} editing={editing} onSaved={load} />
    </Layout>
  );
}
