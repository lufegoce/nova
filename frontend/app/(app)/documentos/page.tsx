"use client";

import { useCallback, useEffect, useState } from "react";
import { UploadCloud } from "lucide-react";
import { DocumentTable } from "@/components/dashboard/DocumentTable";
import { ApprovalModal } from "@/components/dashboard/ApprovalModal";
import { TraceChat } from "@/components/dashboard/TraceChat";
import { DianPanel } from "@/components/dashboard/DianPanel";
import { UploadPdfModal } from "@/components/dashboard/UploadPdfModal";
import { PdfPreviewModal } from "@/components/dashboard/PdfPreviewModal";
import {
  conectarWebSocket,
  listarFacturas,
  type DocumentoDianListado,
  type DocumentoFinanciero,
} from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export default function DocumentosPage() {
  const { sesion } = useAuth();
  const tenantId = sesion?.empresa_actual?.tenant_id;
  const [documentos, setDocumentos] = useState<DocumentoFinanciero[]>([]);
  const [seleccionado, setSeleccionado] = useState<DocumentoFinanciero | null>(null);
  const [pdfEnPreview, setPdfEnPreview] = useState<DocumentoFinanciero | null>(null);
  const [notificacion, setNotificacion] = useState<string | null>(null);
  const [modalSubidaPdf, setModalSubidaPdf] = useState<{ origenDian?: DocumentoDianListado } | null>(null);

  const cargarDocumentos = useCallback(async () => {
    try {
      setDocumentos(await listarFacturas());
    } catch {
      // El backend puede no estar disponible aún en desarrollo local; se reintenta con el WS/polling.
    }
  }, []);

  useEffect(() => {
    cargarDocumentos();
    if (!tenantId) return;

    const ws = conectarWebSocket(tenantId, (data) => {
      if (data.evento === "factura_nueva_dian") {
        setNotificacion(`DIAN: nueva factura ${data.factura?.numero_factura} recibida y acuse enviado.`);
        cargarDocumentos();
      }
      if (data.evento === "documentos_nuevos_pst") {
        setNotificacion(
          `PST: ${data.cantidad} documento(s) nuevo(s) recibido(s) — actualiza el panel DIAN para verlos y subirlos.`
        );
      }
    });

    return () => ws.close();
  }, [cargarDocumentos, tenantId]);

  const pendientes = documentos.filter((d) => d.estado === "aprobacion_pendiente").length;

  return (
    <>
      <header className="flex items-center justify-between border-b border-nova-border p-4">
        <div>
          <h1 className="text-xl font-semibold">Documentos</h1>
          <p className="text-sm text-gray-400">
            {documentos.length} documentos · {pendientes} pendientes de aprobación
          </p>
        </div>

        <button
          onClick={() => setModalSubidaPdf({})}
          className="flex items-center gap-2 rounded-lg bg-nova-accent px-4 py-2 text-sm font-medium text-white hover:bg-blue-600"
        >
          <UploadCloud className="h-4 w-4" />
          Subir factura en PDF
        </button>
      </header>

      {notificacion && (
        <div className="mx-4 mt-3 rounded-lg border border-nova-accent/40 bg-nova-accent/10 px-4 py-2 text-sm text-blue-300">
          {notificacion}
        </div>
      )}

      <div className="flex flex-1 gap-4 overflow-hidden p-4">
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
          <DianPanel onSubirPdf={(origen) => setModalSubidaPdf({ origenDian: origen })} />
          <DocumentTable documentos={documentos} onSeleccionar={setSeleccionado} onVerPdf={setPdfEnPreview} />
        </div>

        <div className="w-96 shrink-0">
          <TraceChat documentos={documentos} />
        </div>
      </div>

      {seleccionado && (
        <ApprovalModal
          documento={seleccionado}
          onCerrar={() => setSeleccionado(null)}
          onResuelto={(doc) => {
            setDocumentos((prev) => prev.map((d) => (d.id === doc.id ? doc : d)));
            setSeleccionado(null);
          }}
        />
      )}

      {pdfEnPreview && <PdfPreviewModal documentoId={pdfEnPreview.id} onCerrar={() => setPdfEnPreview(null)} />}

      {modalSubidaPdf && (
        <UploadPdfModal
          origenDian={modalSubidaPdf.origenDian}
          onCerrar={() => setModalSubidaPdf(null)}
          onSubido={(doc) => {
            setDocumentos((prev) => [doc, ...prev]);
            setModalSubidaPdf(null);
          }}
        />
      )}
    </>
  );
}
