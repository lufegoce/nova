"use client";

import { useCallback, useEffect, useState } from "react";
import { clsx } from "clsx";
import { ScanSearch, ShieldCheck, ShieldAlert } from "lucide-react";
import {
  escanearSeguridadAhora,
  listarAlertasSeguridad,
  resolverAlertaSeguridad,
  type AlertaSeguridad,
  type SeveridadAlerta,
} from "@/lib/api";

const SEVERIDAD_COLOR: Record<SeveridadAlerta, string> = {
  baja: "bg-gray-500/20 text-gray-300",
  media: "bg-amber-500/20 text-amber-300",
  alta: "bg-red-500/20 text-red-300",
};

const TIPO_LABEL: Record<string, string> = {
  aprobaciones_rapidas: "Aprobaciones rápidas",
  pago_rapido_alto_valor: "Pago de alto valor muy rápido",
  fallos_erp_repetidos: "Fallos repetidos con el ERP",
  correcciones_puc_inestables: "Correcciones PUC inestables",
};

export default function SeguridadPage() {
  const [alertas, setAlertas] = useState<AlertaSeguridad[]>([]);
  const [escaneando, setEscaneando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ultimoResultado, setUltimoResultado] = useState<string | null>(null);

  const cargarAlertas = useCallback(async () => {
    try {
      setAlertas(await listarAlertasSeguridad(true));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar alertas");
    }
  }, []);

  useEffect(() => {
    cargarAlertas();
  }, [cargarAlertas]);

  async function escanear() {
    setEscaneando(true);
    setError(null);
    try {
      const resultado = await escanearSeguridadAhora();
      setUltimoResultado(
        resultado.total_alertas_nuevas === 0
          ? "Escaneo completo: no se encontraron anomalías nuevas."
          : `Escaneo completo: ${resultado.total_alertas_nuevas} alerta(s) nueva(s).`
      );
      await cargarAlertas();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al escanear");
    } finally {
      setEscaneando(false);
    }
  }

  async function resolver(id: string) {
    try {
      await resolverAlertaSeguridad(id);
      setAlertas((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al resolver la alerta");
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Seguridad</h1>
            <p className="text-sm text-gray-400">
              El Agente de Seguridad vigila el registro de auditoría y marca patrones anómalos
              (aprobaciones sospechosamente rápidas, pagos de alto valor sin revisión aparente, fallos
              repetidos con el ERP, reglas contables inestables).
            </p>
          </div>
          <button
            onClick={escanear}
            disabled={escaneando}
            className="flex shrink-0 items-center gap-2 rounded-lg bg-nova-accent px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
          >
            <ScanSearch className="h-4 w-4" />
            {escaneando ? "Escaneando..." : "Escanear ahora"}
          </button>
        </div>

        {ultimoResultado && (
          <div className="rounded-lg border border-nova-accent/40 bg-nova-accent/10 px-4 py-2 text-sm text-blue-300">
            {ultimoResultado}
          </div>
        )}
        {error && <p className="text-sm text-red-400">{error}</p>}

        {alertas.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-nova-border p-10 text-center text-gray-500">
            <ShieldCheck className="h-8 w-8 text-emerald-500" />
            <p className="text-sm">Sin alertas activas.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {alertas.map((alerta) => (
              <div key={alerta.id} className="rounded-lg border border-nova-border bg-nova-panel p-4">
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4 shrink-0 text-red-400" />
                    <span className="text-sm font-medium">
                      {TIPO_LABEL[alerta.tipo] ?? alerta.tipo}
                    </span>
                    <span className={clsx("rounded-full px-2 py-0.5 text-xs font-medium", SEVERIDAD_COLOR[alerta.severidad])}>
                      {alerta.severidad}
                    </span>
                  </div>
                  <button
                    onClick={() => resolver(alerta.id)}
                    className="shrink-0 text-xs text-gray-400 hover:text-nova-accent"
                  >
                    Marcar resuelta
                  </button>
                </div>
                <p className="text-sm text-gray-300">{alerta.detalle}</p>
                <p className="mt-1 text-xs text-gray-600">
                  {new Date(alerta.creado_en).toLocaleString("es-CO")}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
