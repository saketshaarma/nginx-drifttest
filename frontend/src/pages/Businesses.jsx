import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Building2, Plus, Server, Trash2, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { Layout, PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export default function Businesses() {
  const [businesses, setBusinesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const load = () => {
    setLoading(true);
    api.get("/businesses").then((r) => setBusinesses(r.data)).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const create = async () => {
    if (!name.trim()) return;
    try {
      await api.post("/businesses", { name, description });
      toast.success("Business created");
      setName(""); setDescription(""); setOpen(false);
      load();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/businesses/${id}`);
      toast.success("Business deleted");
      load();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    }
  };

  return (
    <Layout>
      <PageHeader title="Businesses" subtitle="Group node pairs by business unit">
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="new-business-btn" className="bg-sky-500 hover:bg-sky-400 text-white">
              <Plus className="h-4 w-4 mr-1" /> New Business
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#111827] border-slate-800 text-slate-200">
            <DialogHeader>
              <DialogTitle className="font-display">Create Business</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-1.5">
                <Label className="text-xs font-mono uppercase tracking-wider text-slate-400">Name</Label>
                <Input data-testid="business-name-input" value={name} onChange={(e) => setName(e.target.value)}
                  placeholder="Acme Corp" className="bg-[#0B0F19] border-slate-700" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-mono uppercase tracking-wider text-slate-400">Description</Label>
                <Textarea data-testid="business-desc-input" value={description} onChange={(e) => setDescription(e.target.value)}
                  placeholder="Production edge fleet" className="bg-[#0B0F19] border-slate-700" />
              </div>
            </div>
            <DialogFooter>
              <Button data-testid="save-business-btn" onClick={create} className="bg-sky-500 hover:bg-sky-400 text-white">Create</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageHeader>

      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-6">
        {loading ? (
          <div className="text-slate-500 text-sm">Loading…</div>
        ) : businesses.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-700 bg-[#111827]/50 p-12 text-center" data-testid="businesses-empty">
            <Building2 className="h-10 w-10 text-slate-600 mx-auto mb-3" />
            <div className="text-slate-300 font-medium">No businesses yet</div>
            <p className="text-sm text-slate-500 mt-1">Create a business unit to start mapping node pairs.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {businesses.map((b) => (
              <div key={b.id} data-testid={`business-card-${b.id}`} className="group rounded-xl border border-slate-800 bg-[#111827] p-5 hover:border-slate-700 transition-colors fade-up">
                <div className="flex items-start justify-between">
                  <div className="h-10 w-10 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center">
                    <Building2 className="h-5 w-5 text-sky-400" />
                  </div>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <button data-testid={`delete-business-${b.id}`} className="text-slate-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </AlertDialogTrigger>
                    <AlertDialogContent className="bg-[#111827] border-slate-800 text-slate-200">
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete {b.name}?</AlertDialogTitle>
                        <AlertDialogDescription className="text-slate-400">
                          This removes the business and all its node pairs. This cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel className="bg-transparent border-slate-700 text-slate-300">Cancel</AlertDialogCancel>
                        <AlertDialogAction data-testid={`confirm-delete-business-${b.id}`} onClick={() => remove(b.id)} className="bg-red-500 hover:bg-red-400 text-white">Delete</AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
                <h3 className="font-display font-semibold text-slate-100 mt-3">{b.name}</h3>
                <p className="text-sm text-slate-500 mt-1 line-clamp-2 min-h-[20px]">{b.description || "No description"}</p>
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-800">
                  <span className="text-xs text-slate-400 flex items-center gap-1.5">
                    <Server className="h-3.5 w-3.5" /> {b.node_pair_count} node pair{b.node_pair_count === 1 ? "" : "s"}
                  </span>
                  <Link to={`/businesses/${b.id}`} data-testid={`open-business-${b.id}`} className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium">
                    Manage <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
