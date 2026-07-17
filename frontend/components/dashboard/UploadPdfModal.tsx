"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Sparkles, X } from "lucide-react";
import type { DocumentoDianListado, DocumentoFinanciero } from "@/lib/api";
import { extraerDatosFacturaPdf, ingestarFacturaPdf } from "@/lib/api";

interface Props {
  /** Si se abrió desde una fila del listado DIAN, se usa para precargar campos y enlazar el CUFE. */
  origenDian?: DocumentoDianListado;
  onCerrar: () => void;
  onSubido: (doc: DocumentoFinanciero) => void;
}

const ESTADO_ETIQUETA: Record<string, string> = {
  causado: "Causado",
  aprobacion_pendiente: "Pendiente de aprobación",
  nuevo: "Nuevo",
  validado: "Validado",
  pagado: "Pagado",
  con_error: "Con error",
  rechazado: "Rechazado",
};

/**
 * Formulario de ingesta manual del PDF descargado por el usuario (portal
 * DIAN resolviendo captcha, o vía el PST). Al elegir el archivo, Claude lee
 * el PDF directamente y propone NIT/razón social/número/total/CUFE — el
 * usuario siempre puede revisar y corregir antes de confirmar.
 *
 * El Agente Contable clasifica la cuenta PUC en el mismo request de subida
 * (ver AgentOrchestrator.procesar_pdf_manual, auto_causar=True) — este modal
 * muestra ese resultado antes de cerrarse, en vez de cerrarse en silencio y
 * obligar a buscarlo después en la tabla de documentos.
 */
export function UploadPdfModal({ origenDian, onCerrar, onSubido }: Props) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [nitEmisor, setNitEmisor] = useState(origenDian?.nit_emisor ?? "");
  const [razonSocial, setRazonSocial] = useState(origenDian?.razon_social_emisor ?? "");
  const [numeroFactura, setNumeroFactura] = useState(origenDian?.numero_documento ?? "");
  const [total, setTotal] = useState(origenDian?.total ?? "");
  const [cufe, setCufe] = useState(origenDian?.cufe ?? "");
  const [extrayendo, setExtrayendo] = useState(false);
  const [avisoExtraccion, setAvisoExtraccion] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultado, setResultado] = useState<DocumentoFinanciero | null>(null);

  // La vista previa se arma desde el archivo elegido en el navegador — no
  // hace falta subirlo primero para poder verlo. Los .zip que entrega la
  // DIAN no se pueden previsualizar así (el navegador no renderiza zips);
  // en ese caso solo se avisa que la vista previa no está disponible.
  useEffect(() => {
    if (!archivo || archivo.type !== "application/pdf") {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(archivo);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [archivo]);

  async function alElegirArchivo(nuevoArchivo: File | null) {
    setArchivo(nuevoArchivo);
    setAvisoExtraccion(null);
    if (!nuevoArchivo) return;

    setExtrayendo(true);
    try {
      const propuesta = await extraerDatosFacturaPdf(nuevoArchivo);
      if (!propuesta.extraido_automaticamente) {
        setAvisoExtraccion(propuesta.razon ?? "No se pudo extraer automáticamente; diligencia los campos.");
      } else {
        setAvisoExtraccion("Datos leídos de la factura. Revísalos antes de procesar.");
        // Solo completa los campos que sigan vacíos: no pisa lo que ya vino del listado DIAN.
        setNitEmisor((prev) => prev || propuesta.nit_emisor || "");
        setRazonSocial((prev) => prev || propuesta.razon_social_emisor || "");
        setNumeroFactura((prev) => prev || propuesta.numero_factura || "");
        setTotal((prev) => prev || (propuesta.total != null ? String(propuesta.total) : ""));
        setCufe((prev) => prev || propuesta.cufe || "");
      }
    } catch (e) {
      setAvisoExtraccion(e instanceof Error ? e.message : "No se pudo leer la factura");
    } finally {
      setExtrayendo(false);
    }
  }

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
        cufe: cufe || undefined,
      });
      // Se avisa al padre de una vez (la fila ya existe y debe verse en la
      // tabla), pero el modal se queda abierto mostrando el resultado de la
      // clasificación contable hasta que el usuario pulse "Listo".
      onSubido(doc);
      setResultado(doc);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al subir la factura");
    } finally {
      setEnviando(false);
    }
  }

  if (resultado) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
        <div className="w-full max-w-md rounded-xl border border-nova-border bg-nova-panel p-6">
          <div className="mb-4 flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="h-5 w-5" />
            <h3 className="text-lg font-semibold text-gray-100">Factura procesada</h3>
          </div>

          <div className="space-y-3 rounded-lg border border-nova-border bg-nova-bg p-4 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Estado</span>
              <span className="font-medium text-gray-100">
                {ESTADO_ETIQUETA[resultado.estado] ?? resultado.estado}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Cuenta PUC sugerida</span>
              <span className="font-mono font-medium text-gray-100">
                {resultado.cuenta_puc_sugerida ?? "—"}
              </span>
            </div>
            {resultado.estado === "aprobacion_pendiente" && (
              <p className="text-[11px] text-amber-300">
                La cuenta PUC quedó marcada para revisión humana antes de causar el documento —
                revísala en la tabla de documentos.
              </p>
            )}
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={onCerrar}
              className="rounded-lg bg-nova-accent px-4 py-2 text-sm font-medium text-white hover:bg-blue-600"
            >
              Listo
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex max-h-[90vh] w-full max-w-3xl gap-4 rounded-xl border border-nova-border bg-nova-panel p-6">
        <div className="flex w-1/2 flex-col">
          <p className="mb-2 text-xs text-gray-400">Vista previa</p>
          <div className="flex-1 overflow-hidden rounded-lg border border-nova-border bg-nova-bg">
            {previewUrl ? (
              <iframe src={previewUrl} className="h-full w-full bg-white" title="Vista previa de la factura" />
            ) : (
              <div className="flex h-full items-center justify-center p-4 text-center text-xs text-gray-500">
                {archivo
                  ? "Vista previa no disponible para archivos .zip — súbelo y NOVA extrae el PDF de adentro."
                  : "Elegí un archivo para verlo acá."}
              </div>
            )}
          </div>
        </div>

        <div className="flex w-1/2 flex-col overflow-y-auto">
          <div className="mb-4 flex items-start justify-between">
            <h3 className="text-lg font-semibold">Subir factura en PDF</h3>
            <button onClick={onCerrar} className="text-gray-500 hover:text-gray-300">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Archivo PDF o .zip descargado de la DIAN</label>
              <input
                type="file"
                accept="application/pdf,.pdf,.zip,application/zip,application/x-zip-compressed"
                onChange={(e) => alElegirArchivo(e.target.files?.[0] ?? null)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm"
              />
              <p className="mt-1 flex items-center gap-1 text-[11px] text-gray-500">
                {extrayendo ? (
                  <>
                    <Sparkles className="h-3 w-3 animate-pulse" />
                    Leyendo la factura con IA...
                  </>
                ) : (
                  "Si la DIAN te entregó un .zip, súbelo tal cual: NOVA extrae el PDF y propone los campos."
                )}
              </p>
              {avisoExtraccion && <p className="mt-1 text-[11px] text-amber-300">{avisoExtraccion}</p>}
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

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs text-gray-400">Número de factura</label>
                <input
                  value={numeroFactura}
                  onChange={(e) => setNumeroFactura(e.target.value)}
                  className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-400">CUFE</label>
                <input
                  value={cufe}
                  onChange={(e) => setCufe(e.target.value)}
                  className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
                />
              </div>
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
    </div>
  );
}
