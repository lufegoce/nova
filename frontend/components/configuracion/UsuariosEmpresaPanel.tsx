"use client";

import { useEffect, useState } from "react";
import { UserPlus } from "lucide-react";
import { crearUsuarioEmpresa, listarUsuariosEmpresa, type RolUsuarioEmpresa, type UsuarioEmpresa } from "@/lib/api";

interface Props {
  empresaId: string;
}

const ROLES: { valor: RolUsuarioEmpresa; etiqueta: string; descripcion: string }[] = [
  { valor: "administrador", etiqueta: "Administrador", descripcion: "Todo, incluida la gestión de usuarios" },
  { valor: "aprobador", etiqueta: "Aprobador", descripcion: "Aprueba/rechaza y corrige la cuenta PUC al pagar" },
  { valor: "operador", etiqueta: "Operador", descripcion: "Sube facturas y vincula la DIAN; no aprueba pagos" },
  { valor: "consulta", etiqueta: "Consulta", descripcion: "Solo lectura" },
];

const ETIQUETA_ROL: Record<RolUsuarioEmpresa, string> = {
  administrador: "Administrador",
  aprobador: "Aprobador",
  operador: "Operador",
  consulta: "Consulta",
};

export function UsuariosEmpresaPanel({ empresaId }: Props) {
  const [usuarios, setUsuarios] = useState<UsuarioEmpresa[]>([]);
  const [cargando, setCargando] = useState(true);
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  const [rol, setRol] = useState<RolUsuarioEmpresa>("operador");
  const [creando, setCreando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function cargar() {
    setCargando(true);
    try {
      setUsuarios(await listarUsuariosEmpresa(empresaId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar usuarios");
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargar();
  }, [empresaId]);

  async function crear(e: React.FormEvent) {
    e.preventDefault();
    setCreando(true);
    setError(null);
    try {
      const usuario = await crearUsuarioEmpresa(empresaId, { email, password, nombre, rol });
      setUsuarios((prev) => [...prev, usuario]);
      setMostrarFormulario(false);
      setEmail("");
      setPassword("");
      setNombre("");
      setRol("operador");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al crear el usuario");
    } finally {
      setCreando(false);
    }
  }

  return (
    <div className="rounded-lg border border-nova-border bg-nova-panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">Usuarios de la empresa</h2>
          <p className="text-xs text-gray-500">Quién puede entrar a la plataforma de esta empresa y con qué permisos.</p>
        </div>
        <button
          onClick={() => setMostrarFormulario((v) => !v)}
          className="flex items-center gap-1.5 rounded-lg bg-nova-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-600"
        >
          <UserPlus className="h-3.5 w-3.5" />
          Nuevo usuario
        </button>
      </div>

      {error && <p className="mb-3 text-xs text-red-400">{error}</p>}

      {mostrarFormulario && (
        <form onSubmit={crear} className="mb-4 space-y-3 rounded-lg border border-dashed border-nova-border p-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Nombre *</label>
              <input
                required
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Correo *</label>
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Contraseña temporal *</label>
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Rol *</label>
              <select
                value={rol}
                onChange={(e) => setRol(e.target.value as RolUsuarioEmpresa)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              >
                {ROLES.map((r) => (
                  <option key={r.valor} value={r.valor}>
                    {r.etiqueta}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <p className="text-[11px] text-gray-500">
            {ROLES.find((r) => r.valor === rol)?.descripcion}
          </p>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setMostrarFormulario(false)}
              className="rounded-lg border border-nova-border px-4 py-2 text-sm text-gray-300 hover:bg-nova-bg"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={creando}
              className="rounded-lg bg-nova-accent px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
            >
              {creando ? "Creando..." : "Crear usuario"}
            </button>
          </div>
        </form>
      )}

      {cargando ? (
        <p className="text-xs text-gray-500">Cargando usuarios...</p>
      ) : usuarios.length === 0 ? (
        <p className="rounded-lg border border-dashed border-nova-border p-4 text-center text-xs text-gray-500">
          Todavía no hay usuarios para esta empresa.
        </p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-nova-border">
          <table className="w-full text-left text-xs">
            <thead className="bg-nova-bg text-gray-400">
              <tr>
                <th className="px-3 py-2">Nombre</th>
                <th className="px-3 py-2">Correo</th>
                <th className="px-3 py-2">Rol</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id} className="border-t border-nova-border">
                  <td className="px-3 py-2">{u.nombre}</td>
                  <td className="px-3 py-2 text-gray-400">{u.email}</td>
                  <td className="px-3 py-2">{ETIQUETA_ROL[u.rol]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
