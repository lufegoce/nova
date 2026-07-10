"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { ConfiguracionErp, TipoErp } from "@/lib/api";
import { guardarConfiguracionErp, obtenerConfiguracionErp } from "@/lib/api";

const ERPS: { valor: TipoErp; etiqueta: string; tieneConectorReal: boolean }[] = [
  { valor: "siigo", etiqueta: "SIIGO", tieneConectorReal: true },
  { valor: "alegra", etiqueta: "Alegra", tieneConectorReal: false },
  { valor: "loggro", etiqueta: "Loggro", tieneConectorReal: false },
  { valor: "contapyme", etiqueta: "ContaPyme", tieneConectorReal: false },
  { valor: "siesa", etiqueta: "Siesa ERP", tieneConectorReal: false },
  { valor: "defontana", etiqueta: "Defontana", tieneConectorReal: false },
  { valor: "odoo", etiqueta: "Odoo", tieneConectorReal: false },
  { valor: "sap_business_one", etiqueta: "SAP Business One", tieneConectorReal: false },
];

/**
 * Configuración del ERP contable del tenant. Al aprobar y pagar una factura,
 * el Agente Pagador usa esta configuración para enviar la causación al ERP
 * (ver app/services/erp/ en el backend).
 *
 * SIIGO es el único con conector real implementado (y ese conector, además,
 * no está verificado contra una cuenta real todavía). El resto de ERPs de la
 * lista son puntos de extensión: se pueden seleccionar y usar en modo
 * simulado para probar el flujo de NOVA, pero el envío real a su API
 * respectiva no está construido — agregarlo es una clase más en
 * app/services/erp/, siguiendo el mismo patrón que SIIGO.
 */
export function ErpConfigForm() {
  const [tipoErp, setTipoErp] = useState<TipoErp>("siigo");
  const [username, setUsername] = useState("");
  const [accessKey, setAccessKey] = useState("");
  const [partnerId, setPartnerId] = useState("");
  const [documentIdCompra, setDocumentIdCompra] = useState("");
  const [costCenter, setCostCenter] = useState("");
  const [modoSimulado, setModoSimulado] = useState(true);
  const [activo, setActivo] = useState(true);

  const [configuracionActual, setConfiguracionActual] = useState<ConfiguracionErp | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [mensaje, setMensaje] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);

  const erpSeleccionado = ERPS.find((e) => e.valor === tipoErp)!;

  useEffect(() => {
    obtenerConfiguracionErp().then(setConfiguracionActual).catch(() => {});
  }, []);

  async function guardar() {
    setGuardando(true);
    setMensaje(null);
    try {
      const credenciales: Record<string, string | boolean> = modoSimulado
        ? { modo_simulado: true }
        : {
            username,
            access_key: accessKey,
            partner_id: partnerId,
            document_id_compra: documentIdCompra,
            cost_center: costCenter,
          };

      const resultado = await guardarConfiguracionErp(tipoErp, credenciales, activo);
      setConfiguracionActual(resultado);
      setMensaje({ tipo: "ok", texto: "Configuración guardada." });
    } catch (e) {
      setMensaje({ tipo: "error", texto: e instanceof Error ? e.message : "Error al guardar" });
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold">Configuración · ERP contable</h1>
        <p className="text-sm text-gray-400">
          Al aprobar y pagar una factura, NOVA envía la causación al ERP configurado aquí.
        </p>
      </div>

      {configuracionActual && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>
            ERP configurado: <strong>{configuracionActual.tipo_erp}</strong>
            {" — "}
            {configuracionActual.activo ? "activo" : "inactivo"}
            {configuracionActual.campos_configurados.includes("modo_simulado") && " (modo simulado)"}
          </span>
        </div>
      )}

      <div className="rounded-lg border border-nova-border bg-nova-panel p-5">
        <label className="mb-1 block text-xs text-gray-400">ERP</label>
        <select
          value={tipoErp}
          onChange={(e) => setTipoErp(e.target.value as TipoErp)}
          className="mb-4 w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
        >
          {ERPS.map(({ valor, etiqueta, tieneConectorReal }) => (
            <option key={valor} value={valor}>
              {etiqueta}
              {!tieneConectorReal && " (solo modo simulado por ahora)"}
            </option>
          ))}
        </select>

        <label className="mb-4 flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={modoSimulado} onChange={(e) => setModoSimulado(e.target.checked)} />
          Modo simulado (probar el flujo de NOVA sin enviar nada a un sistema real)
        </label>

        {!modoSimulado && !erpSeleccionado.tieneConectorReal && (
          <div className="mb-4 flex gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <p>
              {erpSeleccionado.etiqueta} todavía no tiene un conector real implementado en NOVA. Actívalo en
              modo simulado mientras se construye, o dinos si necesitas priorizarlo.
            </p>
          </div>
        )}

        {!modoSimulado && erpSeleccionado.tieneConectorReal && (
          <div className="mb-4 space-y-3">
            <div className="flex gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <p>
                El conector {erpSeleccionado.etiqueta} aún no se ha probado contra una cuenta real. Antes de
                usarlo con datos contables reales, valídalo con nosotros o contra su documentación oficial.
              </p>
            </div>

            <div>
              <label className="mb-1 block text-xs text-gray-400">Username (SIIGO)</label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Access Key (SIIGO)</label>
              <input
                type="password"
                value={accessKey}
                onChange={(e) => setAccessKey(e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Partner-Id (asignado por SIIGO)</label>
              <input
                value={partnerId}
                onChange={(e) => setPartnerId(e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs text-gray-400">Tipo de comprobante de compra</label>
                <input
                  value={documentIdCompra}
                  onChange={(e) => setDocumentIdCompra(e.target.value)}
                  className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-400">Centro de costo (opcional)</label>
                <input
                  value={costCenter}
                  onChange={(e) => setCostCenter(e.target.value)}
                  className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
                />
              </div>
            </div>
          </div>
        )}

        <label className="mb-4 flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
          Activo (enviar causación automáticamente al aprobar y pagar)
        </label>

        {mensaje && (
          <p className={`mb-3 text-sm ${mensaje.tipo === "ok" ? "text-emerald-400" : "text-red-400"}`}>
            {mensaje.texto}
          </p>
        )}

        <button
          onClick={guardar}
          disabled={guardando}
          className="rounded-lg bg-nova-accent px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
        >
          {guardando ? "Guardando..." : "Guardar configuración"}
        </button>
      </div>
    </div>
  );
}
