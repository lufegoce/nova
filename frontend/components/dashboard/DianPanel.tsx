"use client";

import { useEffect, useState } from "react";
import { ExternalLink, Link2, UploadCloud } from "lucide-react";
import { clsx } from "clsx";
import type { DocumentoDianListado } from "@/lib/api";
import { listarDocumentosDian, obtenerSesionDian, obtenerUrlPortalDian } from "@/lib/api";
import { LinkDianModal } from "./LinkDianModal";

interface Props {
  onSubirPdf: (origen: DocumentoDianListado) => void;
}

/**
 * Panel semi-automático de la DIAN: NOVA lista los documentos recibidos
 * usando la sesión vinculada; la descarga del PDF la hace el humano en el
 * portal real (exige captcha), y luego la sube con "Subir PDF" para que el
 * Agente Receptor la procese.
 */
export function DianPanel({ onSubirPdf }: Props) {
  const [vinculado, setVinculado] = useState<boolean | null>(null);
  const [documentos, setDocumentos] = useState<DocumentoDianListado[]>([]);
  const [urlPortal, setUrlPortal] = useState<string>("https://catalogo-vpfe.dian.gov.co/Document/Received");
  const [mostrarModalVinculo, setMostrarModalVinculo] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function verificarSesion() {
    const sesion = await obtenerSesionDian().catch(() => null);
    setVinculado(sesion !== null);
    return sesion !== null;
  }

  async function cargarDocumentos() {
    setCargando(true);
    setError(null);
    try {
      setDocumentos(await listarDocumentosDian());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al listar documentos DIAN");
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    verificarSesion().then((ok) => ok && cargarDocumentos());
    obtenerUrlPortalDian().then(setUrlPortal).catch(() => {});
  }, []);

  return (
    <div className="rounded-lg border border-nova-border bg-nova-panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">Documentos recibidos — DIAN</h2>
          <p className="text-xs text-gray-500">
            {vinculado ? "Sesión vinculada · listado automático" : "Sin sesión vinculada"}
          </p>
        </div>
        <div className="flex gap-2">
          {vinculado && (
            <button
              onClick={cargarDocumentos}
              disabled={cargando}
              className="rounded-lg border border-nova-border px-3 py-1.5 text-xs text-gray-300 hover:bg-nova-bg disabled:opacity-50"
            >
              {cargando ? "Actualizando..." : "Actualizar"}
            </button>
          )}
          <button
            onClick={() => setMostrarModalVinculo(true)}
            className="flex items-center gap-1.5 rounded-lg bg-nova-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-600"
          >
            <Link2 className="h-3.5 w-3.5" />
            {vinculado ? "Re-vincular" : "Vincular sesión DIAN"}
          </button>
        </div>
      </div>

      {error && <p className="mb-3 text-xs text-red-400">{error}</p>}

      {!vinculado && (
        <p className="rounded-lg border border-dashed border-nova-border p-4 text-center text-xs text-gray-500">
          Vincula la sesión pegando el enlace que te llega por correo de la DIAN para listar
          automáticamente los documentos recibidos.
        </p>
      )}

      {vinculado && documentos.length === 0 && !cargando && (
        <p className="rounded-lg border border-dashed border-nova-border p-4 text-center text-xs text-gray-500">
          No hay documentos en el rango consultado.
        </p>
      )}

      {vinculado && documentos.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-nova-border">
          <table className="w-full text-left text-xs">
            <thead className="bg-nova-bg text-gray-400">
              <tr>
                <th className="px-3 py-2">CUFE</th>
                <th className="px-3 py-2">Emisor</th>
                <th className="px-3 py-2">Número</th>
                <th className="px-3 py-2">Estado</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {documentos.map((doc) => (
                <tr key={doc.id} className="border-t border-nova-border">
                  <td className="px-3 py-2 font-mono text-gray-400">{doc.cufe.slice(0, 12)}…</td>
                  <td className="px-3 py-2">{doc.razon_social_emisor ?? doc.nit_emisor ?? "—"}</td>
                  <td className="px-3 py-2">{doc.numero_documento ?? "—"}</td>
                  <td className="px-3 py-2">
                    <span
                      className={clsx(
                        "rounded-full px-2 py-0.5",
                        doc.estado_descarga === "descargado"
                          ? "bg-emerald-500/20 text-emerald-300"
                          : "bg-amber-500/20 text-amber-300"
                      )}
                    >
                      {doc.estado_descarga === "descargado" ? "Descargado" : "Pendiente"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex justify-end gap-2">
                      <a
                        href={urlPortal}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-gray-400 hover:text-nova-accent"
                        title="Abrir en el portal DIAN para descargar (requiere resolver captcha)"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                      {doc.estado_descarga === "pendiente" && (
                        <button
                          onClick={() => onSubirPdf(doc)}
                          className="flex items-center gap-1 text-nova-accent hover:underline"
                        >
                          <UploadCloud className="h-3.5 w-3.5" />
                          Subir PDF
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {mostrarModalVinculo && (
        <LinkDianModal
          onCerrar={() => setMostrarModalVinculo(false)}
          onVinculado={() => {
            setMostrarModalVinculo(false);
            verificarSesion().then((ok) => ok && cargarDocumentos());
          }}
        />
      )}
    </div>
  );
}
