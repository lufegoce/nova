"use client";

import { useEffect, useState } from "react";
import { ExternalLink, Link2, UploadCloud } from "lucide-react";
import { clsx } from "clsx";
import { ApiError } from "@/lib/api";
import type { DocumentoDianListado } from "@/lib/api";
import { listarDocumentosDian, obtenerSesionDian, obtenerUrlPortalDian } from "@/lib/api";
import { LinkDianModal } from "./LinkDianModal";

function hace30Dias(): string {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() - 30);
  return fecha.toISOString().slice(0, 10);
}

function hoy(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatearFecha(valor: string | null): string {
  if (!valor) return "—";
  const fecha = new Date(valor);
  return Number.isNaN(fecha.getTime()) ? "—" : fecha.toLocaleDateString("es-CO");
}

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
  const [fechaInicio, setFechaInicio] = useState(hace30Dias());
  const [fechaFin, setFechaFin] = useState(hoy());

  async function verificarSesion() {
    const sesion = await obtenerSesionDian().catch(() => null);
    setVinculado(sesion !== null);
    return sesion !== null;
  }

  async function cargarDocumentos() {
    setCargando(true);
    setError(null);
    try {
      setDocumentos(await listarDocumentosDian({ fechaInicio, fechaFin }));
    } catch (e) {
      // 409 = sin sesión vinculada o sesión expirada (ver DianAuthError en el
      // backend): en vez de dejar al usuario leyendo un mensaje de error,
      // reabrimos el modal para que pegue un enlace nuevo. Un 502 (portal de
      // la DIAN caído) sí se muestra como error, porque un enlace nuevo no
      // lo arregla.
      if (e instanceof ApiError && e.status === 409) {
        setVinculado(false);
        setMostrarModalVinculo(true);
      }
      setError(e instanceof Error ? e.message : "Error al listar documentos DIAN");
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    verificarSesion().then((ok) => {
      if (ok) {
        cargarDocumentos();
      } else {
        setMostrarModalVinculo(true);
      }
    });
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
          <button
            onClick={() => setMostrarModalVinculo(true)}
            className="flex items-center gap-1.5 rounded-lg bg-nova-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-600"
          >
            <Link2 className="h-3.5 w-3.5" />
            {vinculado ? "Re-vincular" : "Vincular sesión DIAN"}
          </button>
        </div>
      </div>

      {vinculado && (
        <div className="mb-3 flex flex-wrap items-end gap-2 text-xs text-gray-400">
          <label className="flex flex-col gap-1">
            Desde
            <input
              type="date"
              value={fechaInicio}
              max={fechaFin}
              onChange={(e) => setFechaInicio(e.target.value)}
              className="rounded-lg border border-nova-border bg-nova-bg px-2 py-1 text-gray-200"
            />
          </label>
          <label className="flex flex-col gap-1">
            Hasta
            <input
              type="date"
              value={fechaFin}
              min={fechaInicio}
              max={hoy()}
              onChange={(e) => setFechaFin(e.target.value)}
              className="rounded-lg border border-nova-border bg-nova-bg px-2 py-1 text-gray-200"
            />
          </label>
          <button
            onClick={cargarDocumentos}
            disabled={cargando}
            className="rounded-lg border border-nova-border px-3 py-1.5 text-gray-300 hover:bg-nova-bg disabled:opacity-50"
          >
            {cargando ? "Actualizando..." : "Filtrar"}
          </button>
        </div>
      )}

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
        <div className="overflow-x-auto rounded-lg border border-nova-border">
          <table className="w-full min-w-[1100px] text-left text-xs">
            <thead className="bg-nova-bg text-gray-400">
              <tr>
                <th className="px-3 py-2">Recepción</th>
                <th className="px-3 py-2">Fecha</th>
                <th className="px-3 py-2">Prefijo</th>
                <th className="px-3 py-2">Nº documento</th>
                <th className="px-3 py-2">Tipo</th>
                <th className="px-3 py-2">NIT Emisor</th>
                <th className="px-3 py-2">Emisor</th>
                <th className="px-3 py-2">NIT Receptor</th>
                <th className="px-3 py-2">Receptor</th>
                <th className="px-3 py-2">Resultado</th>
                <th className="px-3 py-2">Estado RADIAN</th>
                <th className="px-3 py-2">Estado NOVA</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {documentos.map((doc) => (
                <tr key={doc.id} className="border-t border-nova-border">
                  <td className="whitespace-nowrap px-3 py-2 text-gray-400">{formatearFecha(doc.fecha_recepcion)}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-gray-400">{formatearFecha(doc.fecha_emision)}</td>
                  <td className="px-3 py-2">{doc.prefijo ?? "—"}</td>
                  <td className="px-3 py-2" title={doc.cufe}>
                    {doc.numero_documento ?? "—"}
                  </td>
                  <td className="px-3 py-2">{doc.tipo ?? "—"}</td>
                  <td className="px-3 py-2 font-mono">{doc.nit_emisor ?? "—"}</td>
                  <td className="px-3 py-2">{doc.razon_social_emisor ?? "—"}</td>
                  <td className="px-3 py-2 font-mono">{doc.nit_receptor ?? "—"}</td>
                  <td className="px-3 py-2">{doc.razon_social_receptor ?? "—"}</td>
                  <td className="px-3 py-2">{doc.resultado ?? "—"}</td>
                  <td className="px-3 py-2">{doc.estado_radian ?? "—"}</td>
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
            verificarSesion().then((ok) => {
              if (ok) cargarDocumentos();
            });
          }}
        />
      )}
    </div>
  );
}
