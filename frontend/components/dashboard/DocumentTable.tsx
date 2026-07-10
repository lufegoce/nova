"use client";

import { clsx } from "clsx";
import type { DocumentoFinanciero, EstadoDocumento } from "@/lib/api";

const ESTADO_LABEL: Record<EstadoDocumento, string> = {
  nuevo: "Nuevo",
  validado: "Validado",
  causado: "Causado",
  aprobacion_pendiente: "Pendiente aprobación",
  pagado: "Pagado",
  con_error: "Con error",
  rechazado: "Rechazado",
};

const ESTADO_COLOR: Record<EstadoDocumento, string> = {
  nuevo: "bg-gray-500/20 text-gray-300",
  validado: "bg-blue-500/20 text-blue-300",
  causado: "bg-indigo-500/20 text-indigo-300",
  aprobacion_pendiente: "bg-amber-500/20 text-amber-300",
  pagado: "bg-emerald-500/20 text-emerald-300",
  con_error: "bg-red-500/20 text-red-300",
  rechazado: "bg-red-500/20 text-red-400",
};

interface Props {
  documentos: DocumentoFinanciero[];
  onSeleccionar: (doc: DocumentoFinanciero) => void;
  onVerPdf: (doc: DocumentoFinanciero) => void;
}

export function DocumentTable({ documentos, onSeleccionar, onVerPdf }: Props) {
  if (documentos.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-nova-border p-10 text-center text-sm text-gray-500">
        Aún no hay documentos ingresados. Sube el PDF de una factura para iniciar el flujo del Agente Receptor.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-nova-border">
      <table className="w-full text-left text-sm">
        <thead className="bg-nova-panel text-xs uppercase text-gray-400">
          <tr>
            <th className="px-4 py-3">Factura</th>
            <th className="px-4 py-3">Emisor</th>
            <th className="px-4 py-3">Total</th>
            <th className="px-4 py-3">Cuenta PUC</th>
            <th className="px-4 py-3">Estado</th>
            <th className="px-4 py-3">ERP</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {documentos.map((doc) => (
            <tr key={doc.id} className="border-t border-nova-border hover:bg-nova-panel/60">
              <td className="px-4 py-3 font-medium">{doc.numero_factura ?? "—"}</td>
              <td className="px-4 py-3 text-gray-300">
                {doc.razon_social_emisor ?? doc.nit_emisor}
              </td>
              <td className="px-4 py-3 tabular-nums">
                {new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP" }).format(doc.total)}
              </td>
              <td className="px-4 py-3 text-gray-400">{doc.cuenta_puc_sugerida ?? "—"}</td>
              <td className="px-4 py-3">
                <span className={clsx("rounded-full px-2 py-1 text-xs font-medium", ESTADO_COLOR[doc.estado])}>
                  {ESTADO_LABEL[doc.estado]}
                </span>
              </td>
              <td className="px-4 py-3">
                {doc.erp_estado === "no_configurado" && <span className="text-xs text-gray-600">—</span>}
                {doc.erp_estado === "enviado" && (
                  <span
                    className="rounded-full bg-emerald-500/20 px-2 py-1 text-xs font-medium text-emerald-300"
                    title={doc.erp_referencia ? `Ref. ${doc.erp_referencia}` : undefined}
                  >
                    Sincronizado
                  </span>
                )}
                {doc.erp_estado === "error" && (
                  <span
                    className="cursor-help rounded-full bg-red-500/20 px-2 py-1 text-xs font-medium text-red-300"
                    title={doc.erp_detalle_error ?? "Error al enviar al ERP"}
                  >
                    Error ERP
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-right">
                <div className="flex justify-end gap-3">
                  {doc.tiene_pdf && (
                    <button onClick={() => onVerPdf(doc)} className="text-xs text-gray-400 hover:text-nova-accent">
                      Ver PDF
                    </button>
                  )}
                  <button
                    onClick={() => onSeleccionar(doc)}
                    className="text-xs font-medium text-nova-accent hover:underline"
                  >
                    {doc.estado === "aprobacion_pendiente" ? "Revisar" : "Ver detalle"}
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
