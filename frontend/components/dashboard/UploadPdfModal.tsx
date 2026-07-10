"use client";

import { useState } from "react";
import { X } from "lucide-react";
import type { DocumentoDianListado, DocumentoFinanciero } from "@/lib/api";
import { ingestarFacturaPdf } from "@/lib/api";

interface Props {
  /** Si se abrió desde una fila del listado DIAN, se usa para precargar campos y enlazar el CUFE. */
  origenDian?: DocumentoDianListado;
  onCerrar: () => void;
  onSubido: (doc: DocumentoFinanciero) => void;
}

/**
 * Formulario de ingesta manual del PDF descargado por el usuario desde el
 * portal real de la DIAN (después de resolver el captcha él mismo). La
 * extracción automática de campos desde un PDF arbitrario no es confiable,
 * así que el humano confirma NIT/total/número aquí.
 */
export function UploadPdfModal({ origenDian, onCerrar, onSubido }: Props) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [nitEmisor, setNitEmisor] = useState(origenDian?.nit_emisor ?? "");
  const [razonSocial, setRazonSocial] = useState(origenDian?.razon_social_emisor ?? "");
  const [numeroFactura, setNumeroFactura] = useState(origenDian?.numero_documento ?? "");
  const [total, setTotal] = useState(origenDian?.total ?? "");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function subir() {
    if (!archivo || !nitEmisor || !total) {
      setError("Archivo, NIT del emisor y total son obligatorios");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      const doc = await ingestarFacturaPdf({
        archivo,
        nitEmisor,
        total: Number(total),
        razonSocialEmisor: razonSocial || undefined,
        numeroFactura: numeroFactura || undefined,
        cufe: origenDian?.cufe,
      });
      onSubido(doc);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al subir la factura");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded-xl border border-nova-border bg-nova-panel p-6">
        <div className="mb-4 flex items-start justify-between">
          <h3 className="text-lg font-semibold">Subir factura en PDF</h3>
          <button onClick={onCerrar} className="text-gray-500 hover:text-gray-300">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs text-gray-400">Archivo PDF</label>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">NIT emisor *</label>
              <input
                value={nitEmisor}
                onChange={(e) => setNitEmisor(e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Total *</label>
              <input
                type="number"
                value={total}
                onChange={(e) => setTotal(e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs text-gray-400">Razón social del emisor</label>
            <input
              value={razonSocial}
              onChange={(e) => setRazonSocial(e.target.value)}
              className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs text-gray-400">Número de factura</label>
            <input
              value={numeroFactura}
              onChange={(e) => setNumeroFactura(e.target.value)}
              className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
            />
          </div>
        </div>

        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

        <div className="mt-4 flex justify-end gap-3">
          <button
            onClick={onCerrar}
            className="rounded-lg border border-nova-border px-4 py-2 text-sm text-gray-300 hover:bg-nova-bg"
          >
            Cancelar
          </button>
          <button
            disabled={enviando}
            onClick={subir}
            className="rounded-lg bg-nova-accent px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
          >
            {enviando ? "Subiendo..." : "Procesar con NOVA"}
          </button>
        </div>
      </div>
    </div>
  );
}
