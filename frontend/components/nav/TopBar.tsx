"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, ChevronDown, LogOut } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { listarEmpresasContador, seleccionarEmpresa, type Empresa } from "@/lib/api";

export function TopBar() {
  const router = useRouter();
  const { sesion, refrescar, cerrarSesion } = useAuth();
  const [abierto, setAbierto] = useState(false);
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [cambiando, setCambiando] = useState(false);
  const contenedorRef = useRef<HTMLDivElement>(null);

  const esContador = sesion?.rol === "contador";

  useEffect(() => {
    function alHacerClicFuera(e: MouseEvent) {
      if (contenedorRef.current && !contenedorRef.current.contains(e.target as Node)) setAbierto(false);
    }
    document.addEventListener("mousedown", alHacerClicFuera);
    return () => document.removeEventListener("mousedown", alHacerClicFuera);
  }, []);

  async function abrirMenu() {
    if (!esContador) return;
    setAbierto((v) => !v);
    if (empresas.length === 0) {
      setEmpresas(await listarEmpresasContador());
    }
  }

  async function cambiarEmpresa(empresaId: string) {
    setCambiando(true);
    try {
      await seleccionarEmpresa(empresaId);
      await refrescar();
      setAbierto(false);
      router.refresh();
    } finally {
      setCambiando(false);
    }
  }

  async function salir() {
    await cerrarSesion();
    router.push("/login");
  }

  if (!sesion) return null;

  return (
    <header className="flex items-center justify-between border-b border-nova-border bg-nova-panel px-6 py-3">
      <div ref={contenedorRef} className="relative">
        <button
          onClick={abrirMenu}
          disabled={!esContador}
          className="flex items-center gap-2 rounded-lg border border-nova-border bg-nova-bg px-3 py-1.5 text-sm disabled:cursor-default"
        >
          <Building2 className="h-4 w-4 text-nova-accent" />
          <span className="font-medium">{sesion.empresa_actual?.nombre ?? "Sin empresa"}</span>
          {esContador && <ChevronDown className="h-3.5 w-3.5 text-gray-500" />}
        </button>

        {abierto && (
          <div className="absolute left-0 top-full z-20 mt-1 w-64 rounded-lg border border-nova-border bg-nova-panel py-1 shadow-xl">
            {empresas.length === 0 ? (
              <p className="px-3 py-2 text-xs text-gray-500">Cargando empresas...</p>
            ) : (
              empresas.map((empresa) => (
                <button
                  key={empresa.id}
                  onClick={() => cambiarEmpresa(empresa.id)}
                  disabled={cambiando}
                  className="flex w-full flex-col items-start px-3 py-2 text-left text-sm hover:bg-nova-bg disabled:opacity-50"
                >
                  <span className="font-medium">{empresa.nombre}</span>
                  {empresa.nit && <span className="text-xs text-gray-500">NIT {empresa.nit}</span>}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm font-medium">{sesion.nombre}</p>
          <p className="text-xs text-gray-500">{esContador ? "Contador" : "Usuario de empresa"}</p>
        </div>
        <button
          onClick={salir}
          className="flex items-center gap-1.5 rounded-lg border border-nova-border px-3 py-1.5 text-xs text-gray-400 hover:text-red-400"
        >
          <LogOut className="h-3.5 w-3.5" />
          Salir
        </button>
      </div>
    </header>
  );
}
