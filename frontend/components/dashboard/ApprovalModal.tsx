"use client";

import { useState } from "react";
import { GraduationCap, X } from "lucide-react";
import type { DocumentoFinanciero } from "@/lib/api";
import { aprobarFactura } from "@/lib/api";

interface Props {
  documento: DocumentoFinanciero;
  onCerrar: () => void;
  onResuelto: (doc: DocumentoFinanciero) => void;
}

/**
 * Modal de aprobación humana (human-in-the-loop). El agente ya propuso la
 * cuenta PUC y las retenciones; el humano decide antes de que el Agente
 * Pagador ejecute el pago.
 *
 * La cuenta PUC es editable: si el humano la corrige, el Agente Contable
 * guarda esa corrección como regla aprendida por NIT del emisor, para que la
 * próxima factura del mismo proveedor se clasifique sola.
 */
export function ApprovalModal({ documento, onCerrar, onResuelto }: Props) {
  const [comentario, setComentario] = useState("");
  const [cuentaPuc, setCuentaPuc] = useState(documento.cuenta_puc_sugerida ?? "");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cuentaFueCorregida = cuentaPuc.trim() !== "" && cuentaPuc.trim() !== documento.cuenta_puc_sugerida;

  async function resolver(aprobado: boolean) {
    setEnviando(true);
    setError(null);
    try {
      const actualizado = await aprobarFactura(
        documento.id,
        aprobado,
        "contador@empresa.com",
        comentario,
        aprobado && cuentaFueCorregida ? cuentaPuc.trim() : undefined
      );
      onResuelto(actualizado);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error inesperado");
    } finally {
      setEnviando(false);
    }
  }

  const retefuente = documento.retenciones?.reteFuente;
  const reteica = documento.retenciones?.reteICA;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded-xl border border-nova-border bg-nova-panel p-6">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h3 className="text-lg font-semibold">Aprobar factura {documento.numero_factura}</h3>
            <p className="text-sm text-gray-400">{documento.razon_social_emisor ?? documento.nit_emisor}</p>
          </div>
          <button onClick={onCerrar} className="text-gray-500 hover:text-gray-300">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mb-4 space-y-3 rounded-lg border border-nova-border bg-nova-bg p-4 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Total factura</span>
            <span className="font-medium">
              {new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP" }).format(documento.total)}
            </span>
          </div>

          <div>
            <label className="mb-1 block text-xs text-gray-400">
              Cuenta PUC sugerida (Agente Contable) — puedes corregirla
            </label>
            <input
              value={cuentaPuc}
              onChange={(e) => setCuentaPuc(e.target.value)}
              className="w-full rounded-lg border border-nova-border bg-nova-panel px-3 py-1.5 text-sm font-medium outline-none focus:border-nova-accent"
            />
            {cuentaFueCorregida && (
              <p className="mt-1 flex items-center gap-1 text-xs text-emerald-400">
                <GraduationCap className="h-3.5 w-3.5" />
                Al aprobar, NOVA aprenderá que {documento.razon_social_emisor ?? documento.nit_emisor} usa esta
                cuenta y la aplicará sola la próxima vez.
              </p>
            )}
          </div>

          {retefuente && (
            <div className="flex justify-between">
              <span className="text-gray-400">ReteFuente</span>
              <span className="font-medium">
                {new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP" }).format(retefuente.valor)}
              </span>
            </div>
          )}
          {reteica && (
            <div className="flex justify-between">
              <span className="text-gray-400">ReteICA</span>
              <span className="font-medium">
                {new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP" }).format(reteica.valor)}
              </span>
            </div>
          )}
        </div>

        <textarea
          value={comentario}
          onChange={(e) => setComentario(e.target.value)}
          placeholder="Comentario opcional para el registro de auditoría..."
          className="mb-4 w-full rounded-lg border border-nova-border bg-nova-bg p-3 text-sm outline-none focus:border-nova-accent"
          rows={2}
        />

        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-3">
          <button
            disabled={enviando}
            onClick={() => resolver(false)}
            className="rounded-lg border border-nova-border px-4 py-2 text-sm text-gray-300 hover:bg-nova-bg disabled:opacity-50"
          >
            Rechazar
          </button>
          <button
            disabled={enviando}
            onClick={() => resolver(true)}
            className="rounded-lg bg-nova-accent px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
          >
            Aprobar y pagar
          </button>
        </div>
      </div>
    </div>
  );
}
