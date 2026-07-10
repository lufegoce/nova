"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { obtenerPdfBlobUrl } from "@/lib/api";

interface Props {
  documentoId: string;
  onCerrar: () => void;
}

export function PdfPreviewModal({ documentoId, onCerrar }: Props) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let urlActual: string | null = null;
    obtenerPdfBlobUrl(documentoId)
      .then((url) => {
        urlActual = url;
        setBlobUrl(url);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Error al cargar el PDF"));

    return () => {
      if (urlActual) URL.revokeObjectURL(urlActual);
    };
  }, [documentoId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex h-[90vh] w-full max-w-3xl flex-col rounded-xl border border-nova-border bg-nova-panel p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-300">Previsualización PDF</h3>
          <button onClick={onCerrar} className="text-gray-500 hover:text-gray-300">
            <X className="h-5 w-5" />
          </button>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        {!error && !blobUrl && <p className="text-sm text-gray-500">Cargando PDF...</p>}
        {blobUrl && (
          <iframe src={blobUrl} className="flex-1 rounded-lg border border-nova-border bg-white" title="Factura PDF" />
        )}
      </div>
    </div>
  );
}
