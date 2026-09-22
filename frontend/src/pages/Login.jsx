import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ServerCog, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@driftwatch.io");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const res = await login(email, password);
    setLoading(false);
    if (res.ok) navigate("/");
    else setError(res.error);
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center px-4 relative overflow-hidden">
      <div className="absolute inset-0 opacity-40" style={{ backgroundImage: "radial-gradient(circle at 20% 20%, rgba(14,165,233,0.12), transparent 40%), radial-gradient(circle at 80% 80%, rgba(99,102,241,0.10), transparent 40%)" }} />
      <div className="relative w-full max-w-md fade-up">
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="h-11 w-11 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center">
            <ServerCog className="h-6 w-6 text-sky-400" />
          </div>
          <div>
            <div className="font-display font-extrabold text-2xl text-slate-100 leading-none">DriftWatch</div>
            <div className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mt-1">nginx config drift & itsm</div>
          </div>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-[#111827] p-8 shadow-2xl">
          <h1 className="font-display text-lg font-semibold text-slate-100 mb-1">Sign in to console</h1>
          <p className="text-sm text-slate-500 mb-6">Access the configuration drift command center.</p>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-xs font-mono uppercase tracking-wider text-slate-400">Email</Label>
              <Input
                id="email"
                data-testid="login-email-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-[#0B0F19] border-slate-700 text-slate-100"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-xs font-mono uppercase tracking-wider text-slate-400">Password</Label>
              <Input
                id="password"
                data-testid="login-password-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-[#0B0F19] border-slate-700 text-slate-100"
                required
              />
            </div>
            {error && (
              <div data-testid="login-error" className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
                {error}
              </div>
            )}
            <Button
              type="submit"
              data-testid="login-submit-btn"
              disabled={loading}
              className="w-full bg-sky-500 hover:bg-sky-400 text-white font-medium"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Sign in"}
            </Button>
          </form>
          <p className="text-[11px] text-slate-600 mt-5 text-center font-mono">
            demo · admin@driftwatch.io / admin123
          </p>
        </div>
      </div>
    </div>
  );
}
