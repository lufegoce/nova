"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { clsx } from "clsx";
import { Bot, Lock, Mail } from "lucide-react";
import { loginContador, loginEmpresa } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

type Perfil = "empresa" | "contador";

export default function LoginPage() {
  const router = useRouter();
  const { refrescar } = useAuth();
  const [perfil, setPerfil] = useState<Perfil>("empresa");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      if (perfil === "contador") {
        await loginContador(email, password);
      } else {
        await loginEmpresa(email, password);
      }
      await refrescar();
      router.push("/documentos");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo iniciar sesión");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-nova-bg px-4 text-gray-100">
      <div className="w-full max-w-sm rounded-xl border border-nova-border bg-nova-panel p-8">
        <div className="mb-6 flex items-center justify-center gap-2">
          <Bot className="h-7 w-7 text-nova-accent" />
          <span className="text-xl font-semibold">NOVA</span>
        </div>

        <div className="mb-6 flex rounded-lg bg-nova-bg p-1">
          <button
            type="button"
            onClick={() => setPerfil("empresa")}
            className={clsx(
              "flex-1 rounded-md py-1.5 text-sm font-medium transition-colors",
              perfil === "empresa" ? "bg-nova-accent text-white" : "text-gray-400 hover:text-gray-200"
            )}
          >
            Empresa
          </button>
          <button
            type="button"
            onClick={() => setPerfil("contador")}
            className={clsx(
              "flex-1 rounded-md py-1.5 text-sm font-medium transition-colors",
              perfil === "contador" ? "bg-nova-accent text-white" : "text-gray-400 hover:text-gray-200"
            )}
          >
            Contador
          </button>
        </div>

        <p className="mb-5 text-center text-xs text-gray-500">
          {perfil === "empresa"
            ? "Acceso para el equipo de la empresa."
            : "Acceso para el contador: administra todas tus empresas registradas."}
        </p>

        <form onSubmit={enviar} className="space-y-4">
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input
              type="email"
              required
              placeholder="Correo electrónico"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-nova-border bg-nova-bg py-2 pl-9 pr-3 text-sm outline-none focus:border-nova-accent"
            />
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input
              type="password"
              required
              placeholder="Contraseña"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-nova-border bg-nova-bg py-2 pl-9 pr-3 text-sm outline-none focus:border-nova-accent"
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={enviando}
            className="w-full rounded-lg bg-nova-accent py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
          >
            {enviando ? "Ingresando..." : "Ingresar"}
          </button>
        </form>

        <p className="mt-6 text-center text-[11px] text-gray-600">
          Próximamente: verificación en dos pasos (2FA) para ambos perfiles.
        </p>
      </div>
    </div>
  );
}
