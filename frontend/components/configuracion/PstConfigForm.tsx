"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, PlugZap, RefreshCw } from "lucide-react";
import { clsx } from "clsx";
import type { ConfiguracionPst, DocumentoRecibidoPst, TipoPst } from "@/lib/api";
import {
  guardarConfiguracionPst,
  listarDocumentosRecibidosPst,
  obtenerConfiguracionPst,
  probarConexionPst,
} from "@/lib/api";

/**
 * Integración con el PST (Proveedor de Servicios Tecnológicos autorizado por
 * la DIAN). A diferencia del panel DIAN (que depende de que un humano
 * resuelva el captcha del portal), esta vía consulta los documentos
 * recibidos directamente vía la API del PST — sin captcha de por medio,
 * porque es un canal pensado para integración de software.
 *
 * El conector de Factus (ver app/services/pst/factus_connector.py) está
 * parcialmente verificado: la autenticación y el listado están confirmados
 * contra la documentación pública, pero los nombres exactos de los campos
 * de cada factura no se han probado contra una respuesta real todavía.
 */
export function PstConfigForm() {
  const [tipoPst] = useState<TipoPst>("factus");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [modoSimulado, setModoSimulado] = useState(true);
  const [activo, setActivo] = useState(true);

  const [configuracionActual, setConfiguracionActual] = useState<ConfiguracionPst | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [probando, setProbando] = useState(false);
  const [mensaje, setMensaje] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);

  const [documentos, setDocumentos] = useState<DocumentoRecibidoPst[]>([]);
  const [cargandoDocumentos, setCargandoDocumentos] = useState(false);
  const [errorDocumentos, setErrorDocumentos] = useState<string | null>(null);

  useEffect(() => {
    obtenerConfiguracionPst().then(setConfiguracionActual).catch(() => {});
  }, []);

  async function guardar() {
    setGuardando(true);
    setMensaje(null);
    try {
      const credenciales: Record<string, string | boolean> = modoSimulado
        ? { modo_simulado: true }
        : { client_id: clientId, client_secret: clientSecret, username, password };

      const resultado = await guardarConfiguracionPst(tipoPst, credenciales, activo);
      setConfiguracionActual(resultado);
      setMensaje({ tipo: "ok", texto: "Configuración guardada." });
    } catch (e) {
      setMensaje({ tipo: "error", texto: e instanceof Error ? e.message : "Error al guardar" });
    } finally {
      setGuardando(false);
    }
  }

  async function probar() {
    setProbando(true);
    setMensaje(null);
    try {
      await probarConexionPst();
      setMensaje({ tipo: "ok", texto: "Conexión exitosa: las credenciales funcionan." });
    } catch (e) {
      setMensaje({ tipo: "error", texto: e instanceof Error ? e.message : "No se pudo conectar" });
    } finally {
      setProbando(false);
    }
  }

  async function cargarDocumentos() {
    setCargandoDocumentos(true);
    setErrorDocumentos(null);
    try {
      setDocumentos(await listarDocumentosRecibidosPst());
    } catch (e) {
      setErrorDocumentos(e instanceof Error ? e.message : "Error al listar documentos");
    } finally {
      setCargandoDocumentos(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold">Configuración · PST (recepción sin captcha)</h1>
        <p className="text-sm text-gray-400">
          Consulta los documentos que le llegan a la empresa directamente por la API del PST, sin depender de que
          un humano resuelva el captcha del portal de la DIAN.
        </p>
      </div>

      {configuracionActual && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>
            PST configurado: <strong>{configuracionActual.tipo_pst}</strong>
            {" — "}
            {configuracionActual.activo ? "activo" : "inactivo"}
            {configuracionActual.campos_configurados.includes("modo_simulado") && " (modo simulado)"}
          </span>
        </div>
      )}

      <div className="rounded-lg border border-nova-border bg-nova-panel p-5">
        <label className="mb-1 block text-xs text-gray-400">PST</label>
        <select
          value={tipoPst}
          disabled
          className="mb-4 w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm text-gray-400 outline-none"
        >
          <option value="factus">Factus</option>
        </select>

        <label className="mb-4 flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={modoSimulado} onChange={(e) => setModoSimulado(e.target.checked)} />
          Modo simulado (probar el flujo de NOVA sin conectar con Factus real)
        </label>

        {!modoSimulado && (
          <div className="mb-4 space-y-3">
            <div className="flex gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <p>
                El conector de Factus está parcialmente verificado: la autenticación y el listado están confirmados
                contra su documentación pública, pero el detalle exacto de cada factura aún no se ha probado con
                una respuesta real. Usa "Probar conexión" antes de confiar en los datos.
              </p>
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Client ID</label>
              <input
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Client Secret</label>
              <input
                type="password"
                value={clientSecret}
                onChange={(e) => setClientSecret(e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs text-gray-400">Usuario (correo)</label>
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-400">Contraseña</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
                />
              </div>
            </div>
          </div>
        )}

        <label className="mb-4 flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
          Activo
        </label>

        {mensaje && (
          <p className={`mb-3 text-sm ${mensaje.tipo === "ok" ? "text-emerald-400" : "text-red-400"}`}>
            {mensaje.texto}
          </p>
        )}

        <div className="flex gap-3">
          <button
            onClick={guardar}
            disabled={guardando}
            className="rounded-lg bg-nova-accent px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
          >
            {guardando ? "Guardando..." : "Guardar configuración"}
          </button>
          {configuracionActual && (
            <button
              onClick={probar}
              disabled={probando}
              className="flex items-center gap-1.5 rounded-lg border border-nova-border px-4 py-2 text-sm text-gray-300 hover:bg-nova-bg disabled:opacity-50"
            >
              <PlugZap className="h-4 w-4" />
              {probando ? "Probando..." : "Probar conexión"}
            </button>
          )}
        </div>
      </div>

      {configuracionActual && (
        <div className="rounded-lg border border-nova-border bg-nova-panel p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Documentos recibidos (vía PST)</h2>
            <button
              onClick={cargarDocumentos}
              disabled={cargandoDocumentos}
              className="flex items-center gap-1.5 rounded-lg border border-nova-border px-3 py-1.5 text-xs text-gray-300 hover:bg-nova-bg disabled:opacity-50"
            >
              <RefreshCw className={clsx("h-3.5 w-3.5", cargandoDocumentos && "animate-spin")} />
              {cargandoDocumentos ? "Consultando..." : "Consultar ahora"}
            </button>
          </div>

          {errorDocumentos && <p className="mb-3 text-xs text-red-400">{errorDocumentos}</p>}

          {documentos.length === 0 ? (
            <p className="rounded-lg border border-dashed border-nova-border p-4 text-center text-xs text-gray-500">
              Pulsa "Consultar ahora" para traer los documentos recibidos.
            </p>
          ) : (
            <div className="overflow-hidden rounded-lg border border-nova-border">
              <table className="w-full text-left text-xs">
                <thead className="bg-nova-bg text-gray-400">
                  <tr>
                    <th className="px-3 py-2">CUFE</th>
                    <th className="px-3 py-2">Emisor</th>
                    <th className="px-3 py-2">Número</th>
                    <th className="px-3 py-2">Eventos</th>
                  </tr>
                </thead>
                <tbody>
                  {documentos.map((d) => (
                    <tr key={d.cufe} className="border-t border-nova-border">
                      <td className="px-3 py-2 font-mono text-gray-400">{d.cufe.slice(0, 16)}…</td>
                      <td className="px-3 py-2">{d.razon_social_emisor ?? d.nit_emisor ?? "—"}</td>
                      <td className="px-3 py-2">{d.numero_documento ?? "—"}</td>
                      <td className="px-3 py-2">
                        {d.tiene_eventos_pendientes === null
                          ? "—"
                          : d.tiene_eventos_pendientes
                            ? "Pendientes"
                            : "Al día"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
