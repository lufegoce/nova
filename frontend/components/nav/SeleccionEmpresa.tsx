"use client";

import { useEffect, useState } from "react";
import { Building2, Plus } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { crearEmpresaContador, listarEmpresasContador, seleccionarEmpresa, type Empresa } from "@/lib/api";

export function SeleccionEmpresa() {
  const { refrescar } = useAuth();
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [cargando, setCargando] = useState(true);
  const [seleccionando, setSeleccionando] = useState<string | null>(null);
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [nombreNuevo, setNombreNuevo] = useState("");
  const [nitNuevo, setNitNuevo] = useState("");
  const [creando, setCreando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function cargar() {
    setCargando(true);
    try {
      setEmpresas(await listarEmpresasContador());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar empresas");
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargar();
  }, []);

  async function elegir(empresaId: string) {
    setSeleccionando(empresaId);
    try {
      await seleccionarEmpresa(empresaId);
      await refrescar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al seleccionar la empresa");
      setSeleccionando(null);
    }
  }

  async function crear(e: React.FormEvent) {
    e.preventDefault();
    setCreando(true);
    setError(null);
    try {
      const nueva = await crearEmpresaContador({ nombre: nombreNuevo, nit: nitNuevo || undefined });
      setEmpresas((prev) => [...prev, nueva]);
      setMostrarFormulario(false);
      setNombreNuevo("");
      setNitNuevo("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al crear la empresa");
    } finally {
      setCreando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-nova-bg px-4 text-gray-100">
      <div className="w-full max-w-lg">
        <h1 className="mb-1 text-center text-xl font-semibold">Selecciona una empresa</h1>
        <p className="mb-6 text-center text-sm text-gray-400">
          Administras varias empresas en NOVA. Elige con cuál quieres trabajar.
        </p>

        {error && <p className="mb-4 text-center text-sm text-red-400">{error}</p>}

        {cargando ? (
          <p className="text-center text-sm text-gray-500">Cargando empresas...</p>
        ) : (
          <div className="space-y-2">
            {empresas.map((empresa) => (
              <button
                key={empresa.id}
                onClick={() => elegir(empresa.id)}
                disabled={seleccionando !== null}
                className="flex w-full items-center gap-3 rounded-lg border border-nova-border bg-nova-panel px-4 py-3 text-left hover:border-nova-accent disabled:opacity-50"
              >
                <Building2 className="h-5 w-5 shrink-0 text-nova-accent" />
                <div className="flex-1">
                  <p className="text-sm font-medium">{empresa.nombre}</p>
                  {empresa.nit && <p className="text-xs text-gray-500">NIT {empresa.nit}</p>}
                </div>
                {seleccionando === empresa.id && <span className="text-xs text-gray-500">Entrando...</span>}
              </button>
            ))}
          </div>
        )}

        {mostrarFormulario ? (
          <form onSubmit={crear} className="mt-4 space-y-2 rounded-lg border border-dashed border-nova-border p-4">
            <input
              required
              placeholder="Nombre de la empresa"
              value={nombreNuevo}
              onChange={(e) => setNombreNuevo(e.target.value)}
              className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
            />
            <input
              placeholder="NIT (opcional)"
              value={nitNuevo}
              onChange={(e) => setNitNuevo(e.target.value)}
              className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
            />
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={creando}
                className="flex-1 rounded-lg bg-nova-accent py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
              >
                {creando ? "Creando..." : "Crear empresa"}
              </button>
              <button
                type="button"
                onClick={() => setMostrarFormulario(false)}
                className="rounded-lg border border-nova-border px-4 py-2 text-sm text-gray-400"
              >
                Cancelar
              </button>
            </div>
          </form>
        ) : (
          <button
            onClick={() => setMostrarFormulario(true)}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-nova-border py-3 text-sm text-gray-400 hover:border-nova-accent hover:text-nova-accent"
          >
            <Plus className="h-4 w-4" />
            Registrar nueva empresa
          </button>
        )}
      </div>
    </div>
  );
}
