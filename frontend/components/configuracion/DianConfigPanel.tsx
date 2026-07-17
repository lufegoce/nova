"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Link2 } from "lucide-react";
import type { SesionDian } from "@/lib/api";
import { obtenerSesionDian } from "@/lib/api";
import { LinkDianModal } from "@/components/dashboard/LinkDianModal";

/**
 * Registro del token/magic-link de la DIAN, como configuración del tenant
 * (igual que ERP y PST). El token en sí se pega en el mismo LinkDianModal
 * que también se abre automáticamente desde el panel de "Documentos
 * recibidos — DIAN" cuando no hay sesión válida — este panel es la vía
 * manual, para registrarlo o revisarlo desde Configuración sin tener que
 * ir primero a consultar facturas.
 */
export function DianConfigPanel() {
  const [sesion, setSesion] = useState<SesionDian | null>(null);
  const [cargando, setCargando] = useState(true);
  const [mostrarModal, setMostrarModal] = useState(false);

  function cargarSesion() {
    setCargando(true);
    obtenerSesionDian()
      .then(setSesion)
      .finally(() => setCargando(false));
  }

  useEffect(() => {
    cargarSesion();
  }, []);

  return (
    <div className="rounded-lg border border-nova-border bg-nova-panel p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">DIAN — Catálogo de Visualización</h2>
          <p className="text-xs text-gray-500">
            Vincula el enlace que llega al correo de la DIAN para listar automáticamente los
            documentos recibidos, sin depender del captcha del portal.
          </p>
        </div>
        <button
          onClick={() => setMostrarModal(true)}
          className="flex shrink-0 items-center gap-1.5 rounded-lg bg-nova-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-600"
        >
          <Link2 className="h-3.5 w-3.5" />
          {sesion ? "Re-vincular" : "Vincular"}
        </button>
      </div>

      {!cargando && sesion && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>
            Sesión vinculada{sesion.nit_vinculado && ` — NIT ${sesion.nit_vinculado}`}
            {" · "}
            {new Date(sesion.vinculado_en).toLocaleString("es-CO")}
          </span>
        </div>
      )}

      {!cargando && !sesion && (
        <p className="rounded-lg border border-dashed border-nova-border p-4 text-center text-xs text-gray-500">
          Sin sesión vinculada. Pulsa "Vincular" y pega el enlace del correo de la DIAN.
        </p>
      )}

      {mostrarModal && (
        <LinkDianModal
          onCerrar={() => setMostrarModal(false)}
          onVinculado={() => {
            setMostrarModal(false);
            cargarSesion();
          }}
        />
      )}
    </div>
  );
}
