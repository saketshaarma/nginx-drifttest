import { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  Plus, Server, Play, Pencil, Trash2, Clock, ArrowLeft, Loader2, FolderTree, History, X, ArrowRightLeft,
} from "lucide-react";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { Layout, PageHeader } from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const emptyPair = () => ({ _key: crypto.randomUUID(), dc_node: "", dr_node: "", port_dc: 22, port_dr: 22 });
const EMPTY = {
  name: "", folder: "/etc/nginx", ssh_username: "", ssh_password: "",
  pairs: [emptyPair()], exclude_patterns: [], schedule_enabled: false, schedule_interval_minutes: 60,
};

function Field({ label, children }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-mono uppercase tracking-wider text-slate-400">{label}</Label>
      {children}
    </div>
  );
}

function MappingDialog({ open, onOpenChange, businessId, editing, onSaved }) {
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (editing) {
      setForm({
        ...EMPTY, ...editing, ssh_password: "",
        pairs: editing.pairs?.length ? editing.pairs.map((p) => ({ ...p, _key: crypto.randomUUID() })) : [emptyPair()],
        exclude_patterns: editing.exclude_patterns || [],
      });
    } else {
      setForm({ ...EMPTY, pairs: [emptyPair()] });
    }
  }, [editing, open]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const setPair = (i, k, v) => setForm((f) => ({ ...f, pairs: f.pairs.map((p, idx) => idx === i ? { ...p, [k]: v } : p) }));
  const addPair = () => setForm((f) => ({ ...f, pairs: [...f.pairs, emptyPair()] }));
  const removePair = (i) => setForm((f) => ({ ...f, pairs: f.pairs.filter((_, idx) => idx !== i) }));

  const save = async () => {
    if (!form.name.trim()) return toast.error("Mapping name is required");
    const valid = form.pairs
      .filter((p) => p.dc_node.trim() && p.dr_node.trim())
      .map(({ _key, ...rest }) => rest);
    if (valid.length === 0) return toast.error("Add at least one DC↔DR pair");
    setSaving(true);
    try {
      const body = { ...form, pairs: valid };
      if (editing) {
        if (!body.ssh_password) delete body.ssh_password;
        await api.put(`/node-pairs/${editing.id}`, body);
        toast.success("Mapping updated");
      } else {
        await api.post("/node-pairs", { ...body, business_id: businessId });
        toast.success("Mapping created");
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
      <DialogContent className="bg-[#111827] border-slate-800 text-slate-200 max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-display">{editing ? "Edit Mapping" : "New Mapping"}</DialogTitle>
          <DialogDescription className="text-slate-500 text-sm">
            A mapping shares one config folder + SSH credentials across many DC↔DR node pairs.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <Field label="Mapping Name">
            <Input data-testid="np-name-input" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Edge Load Balancer Fleet" className="bg-[#0B0F19] border-slate-700" />
          </Field>
          <Field label="Config Folder">
            <Input data-testid="np-folder-input" value={form.folder} onChange={(e) => set("folder", e.target.value)} placeholder="/etc/nginx" className="bg-[#0B0F19] border-slate-700 font-mono" />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="SSH Username">
              <Input data-testid="np-user-input" value={form.ssh_username} onChange={(e) => set("ssh_username", e.target.value)} placeholder="deploy" className="bg-[#0B0F19] border-slate-700 font-mono" />
            </Field>
            <Field label={editing ? "SSH Password (blank = keep)" : "SSH Password"}>
              <Input data-testid="np-pass-input" type="password" value={form.ssh_password} onChange={(e) => set("ssh_password", e.target.value)} placeholder="••••••••" className="bg-[#0B0F19] border-slate-700 font-mono" />
            </Field>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0B0F19] p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400">DC ↔ DR Node Pairs</span>
              <Button data-testid="add-pair-btn" type="button" size="sm" variant="outline" onClick={addPair} className="h-7 bg-transparent border-slate-700 text-slate-300 hover:bg-slate-800">
                <Plus className="h-3.5 w-3.5 mr-1" /> Add Pair
              </Button>
            </div>
            <div className="space-y-2">
              <div className="grid grid-cols-[1fr_60px_16px_1fr_60px_28px] gap-2 px-1">
                <span className="text-[10px] font-mono uppercase text-slate-500">DC Node</span>
                <span className="text-[10px] font-mono uppercase text-slate-500">Port</span>
                <span></span>
                <span className="text-[10px] font-mono uppercase text-slate-500">DR Node</span>
                <span className="text-[10px] font-mono uppercase text-slate-500">Port</span>
                <span></span>
              </div>
              {form.pairs.map((p, i) => (
                <div key={p._key} data-testid={`pair-row-${i}`} className="grid grid-cols-[1fr_60px_16px_1fr_60px_28px] gap-2 items-center">
                  <Input data-testid={`pair-dc-node-${i}`} value={p.dc_node} onChange={(e) => setPair(i, "dc_node", e.target.value)} placeholder="dc-lb-01" className="h-9 bg-[#111827] border-slate-700 font-mono text-sm" />
                  <Input data-testid={`pair-dc-port-${i}`} type="number" value={p.port_dc} onChange={(e) => setPair(i, "port_dc", parseInt(e.target.value) || 22)} className="h-9 bg-[#111827] border-slate-700 font-mono text-sm px-2" />
                  <ArrowRightLeft className="h-3.5 w-3.5 text-slate-600" />
                  <Input data-testid={`pair-dr-node-${i}`} value={p.dr_node} onChange={(e) => setPair(i, "dr_node", e.target.value)} placeholder="dr-lb-01" className="h-9 bg-[#111827] border-slate-700 font-mono text-sm" />
                  <Input data-testid={`pair-dr-port-${i}`} type="number" value={p.port_dr} onChange={(e) => setPair(i, "port_dr", parseInt(e.target.value) || 22)} className="h-9 bg-[#111827] border-slate-700 font-mono text-sm px-2" />
                  <button data-testid={`remove-pair-${i}`} type="button" onClick={() => removePair(i)} disabled={form.pairs.length === 1} className="text-slate-600 hover:text-red-400 disabled:opacity-30 flex justify-center">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0B0F19] p-3 space-y-2">
            <Field label="Exclude files from comparison (one glob per line)">
              <Textarea
                data-testid="np-exclude-input"
                value={(form.exclude_patterns || []).join("\n")}
                onChange={(e) => set("exclude_patterns", e.target.value.split("\n"))}
                placeholder={"*.log\nssl/*.key\nconf.d/local.conf"}
                rows={3}
                className="bg-[#111827] border-slate-700 font-mono text-sm"
              />
            </Field>
            <p className="text-[11px] text-slate-500">Matches by full relative path or filename. e.g. <span className="font-mono">*.log</span>, <span className="font-mono">ssl/*.key</span>, <span className="font-mono">conf.d/local.conf</span></p>
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
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : editing ? "Save Changes" : "Create Mapping"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function BusinessDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [business, setBusiness] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [runningId, setRunningId] = useState(null);

  const load = useCallback(() => {
    api.get(`/businesses/${id}`).then((r) => setBusiness(r.data)).catch(() => navigate("/businesses"));
    api.get(`/node-pairs?business_id=${id}`).then((r) => setMappings(r.data));
  }, [id, navigate]);

  useEffect(load, [load]);

  const runCompare = async (mid) => {
    setRunningId(mid);
    try {
      const { data } = await api.post(`/node-pairs/${mid}/compare`);
      toast.info("Comparison started", { description: "Connecting via SSH and diffing every DC↔DR pair." });
      navigate(`/runs/${data.id}`);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    } finally {
      setRunningId(null);
    }
  };

  const remove = async (mid) => {
    await api.delete(`/node-pairs/${mid}`);
    toast.success("Mapping deleted");
    load();
  };

  return (
    <Layout>
      <PageHeader title={business?.name || "Business"} subtitle={business?.description}>
        <Button data-testid="new-nodepair-btn" onClick={() => { setEditing(null); setDialogOpen(true); }} className="bg-sky-500 hover:bg-sky-400 text-white">
          <Plus className="h-4 w-4 mr-1" /> New Mapping
        </Button>
      </PageHeader>

      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-6">
        <Link to="/businesses" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 mb-5">
          <ArrowLeft className="h-4 w-4" /> Back to businesses
        </Link>

        {mappings.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-700 bg-[#111827]/50 p-12 text-center" data-testid="nodepairs-empty">
            <Server className="h-10 w-10 text-slate-600 mx-auto mb-3" />
            <div className="text-slate-300 font-medium">No mappings yet</div>
            <p className="text-sm text-slate-500 mt-1">Create a mapping and add DC↔DR node pairs to compare their nginx configs.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {mappings.map((m) => (
              <div key={m.id} data-testid={`nodepair-card-${m.id}`} className="rounded-xl border border-slate-800 bg-[#111827] p-5 fade-up">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-display font-semibold text-slate-100 flex items-center gap-2">
                      {m.name}
                      {m.schedule_enabled && (
                        <span className="text-[10px] font-mono text-sky-400 bg-sky-500/10 border border-sky-500/20 rounded px-1.5 py-0.5 flex items-center gap-1">
                          <Clock className="h-2.5 w-2.5" /> {m.schedule_interval_minutes}m
                        </span>
                      )}
                    </h3>
                    <StatusBadge status={m.last_status || "never"} className="mt-2" pulse={m.last_status === "drift"} />
                  </div>
                  <div className="flex items-center gap-1">
                    <button data-testid={`edit-np-${m.id}`} onClick={() => { setEditing(m); setDialogOpen(true); }} className="p-1.5 text-slate-500 hover:text-slate-200 transition-colors">
                      <Pencil className="h-4 w-4" />
                    </button>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <button data-testid={`delete-np-${m.id}`} className="p-1.5 text-slate-500 hover:text-red-400 transition-colors">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </AlertDialogTrigger>
                      <AlertDialogContent className="bg-[#111827] border-slate-800 text-slate-200">
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete {m.name}?</AlertDialogTitle>
                          <AlertDialogDescription className="text-slate-400">This removes the mapping, all its DC↔DR pairs and its schedule.</AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel className="bg-transparent border-slate-700 text-slate-300">Cancel</AlertDialogCancel>
                          <AlertDialogAction data-testid={`confirm-delete-np-${m.id}`} onClick={() => remove(m.id)} className="bg-red-500 hover:bg-red-400 text-white">Delete</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>

                <div className="mt-4 flex items-center gap-2 text-sm text-slate-400">
                  <FolderTree className="h-3.5 w-3.5 text-slate-500" />
                  <span className="font-mono text-slate-300">{m.folder}</span>
                  <span className="text-slate-600">·</span>
                  <span className="text-xs">{m.pairs?.length || 0} DC↔DR pair{(m.pairs?.length || 0) === 1 ? "" : "s"}</span>
                </div>
                {m.exclude_patterns?.length > 0 && (
                  <div className="mt-1.5 text-[11px] text-slate-500 font-mono" data-testid={`exclude-info-${m.id}`}>
                    excludes: {m.exclude_patterns.join(", ")}
                  </div>
                )}

                <div className="mt-3 space-y-1.5 max-h-32 overflow-y-auto pr-1">
                  {m.pairs?.map((p) => (
                    <div key={p.id} className="flex items-center gap-2 text-xs font-mono text-slate-400 bg-[#0B0F19] rounded px-2.5 py-1.5">
                      <span className="text-amber-400/90">{p.dc_node}:{p.port_dc}</span>
                      <ArrowRightLeft className="h-3 w-3 text-slate-600" />
                      <span className="text-violet-400/90">{p.dr_node}:{p.port_dr}</span>
                    </div>
                  ))}
                </div>

                {m.last_summary && (
                  <div className="flex items-center gap-3 text-xs font-mono pt-3 mt-1">
                    <span className="text-slate-400">{m.last_summary.pairs_drifted}/{m.last_summary.pairs_total} drifted</span>
                    <span className="text-red-400">{m.last_summary.different} diff</span>
                    <span className="text-amber-400">{m.last_summary.only_dc} dc</span>
                    <span className="text-violet-400">{m.last_summary.only_dr} dr</span>
                  </div>
                )}

                <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-800">
                  <Button data-testid={`run-compare-${m.id}`} onClick={() => runCompare(m.id)} disabled={runningId === m.id} size="sm" className="bg-sky-500 hover:bg-sky-400 text-white flex-1">
                    {runningId === m.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Play className="h-3.5 w-3.5 mr-1" /> Run Compare</>}
                  </Button>
                  <Link to={`/runs?mapping_id=${m.id}`} data-testid={`history-np-${m.id}`}>
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

      <MappingDialog open={dialogOpen} onOpenChange={setDialogOpen} businessId={id} editing={editing} onSaved={load} />
    </Layout>
  );
}
