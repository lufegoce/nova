"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Mail, PlugZap } from "lucide-react";
import type { ConfiguracionCorreo } from "@/lib/api";
import { guardarConfiguracionCorreo, obtenerConfiguracionCorreo, probarConexionCorreo } from "@/lib/api";

/**
 * Buzón de correo (IMAP) que NOVA vigila para recibir facturas de
 * proveedores directamente por email, sin depender del captcha del portal
 * DIAN ni de subir el PDF a mano — ni la DIAN ni Factus (PST) exponen el
 * archivo por API (confirmado en vivo, ver docstring de
 * app/services/pst/factus_connector.py). Un Celery Beat corre
 * sincronizar_correo_facturas_task cada 5 minutos: sube los .xml
 * directamente (causación automática) y los .pdf/.zip solo si la lectura
 * con IA es confiable; lo demás queda para revisión manual en Documentos.
 */
export function CorreoConfigForm() {
  const [host, setHost] = useState("");
  const [puerto, setPuerto] = useState(993);
  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [carpeta, setCarpeta] = useState("INBOX");
  const [activo, setActivo] = useState(true);

  const [configuracionActual, setConfiguracionActual] = useState<ConfiguracionCorreo | null>(null);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [probando, setProbando] = useState(false);
  const [mensaje, setMensaje] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);

  useEffect(() => {
    obtenerConfiguracionCorreo()
      .then((config) => {
        setConfiguracionActual(config);
        if (config) {
          setHost(config.host);
          setPuerto(config.puerto);
          setUsuario(config.usuario);
          setCarpeta(config.carpeta);
          setActivo(config.activo);
        }
      })
      .finally(() => setCargando(false));
  }, []);

  async function guardar() {
    if (!host || !usuario || !password) {
      setMensaje({ tipo: "error", texto: "Host, usuario y contraseña son obligatorios" });
      return;
    }
    setGuardando(true);
    setMensaje(null);
    try {
      const resultado = await guardarConfiguracionCorreo({ host, puerto, usuario, password, carpeta, activo });
      setConfiguracionActual(resultado);
      setPassword(""); // ya se guardó; no la dejamos visible en el formulario
      setMensaje({ tipo: "ok", texto: "Configuración guardada. NOVA revisará este buzón cada 5 minutos." });
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
      await probarConexionCorreo();
      setMensaje({ tipo: "ok", texto: "Conexión exitosa: las credenciales del buzón funcionan." });
    } catch (e) {
      setMensaje({ tipo: "error", texto: e instanceof Error ? e.message : "No se pudo conectar" });
    } finally {
      setProbando(false);
    }
  }

  if (cargando) return null;

  return (
    <div className="mx-auto w-full max-w-xl space-y-6 p-6">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-semibold">
          <Mail className="h-5 w-5" />
          Configuración · Correo de facturas
        </h1>
        <p className="text-sm text-gray-400">
          NOVA revisa este buzón por IMAP y sube automáticamente las facturas que los proveedores envíen ahí: los
          .xml se causan solos, los .pdf/.zip solo si la lectura con IA es confiable.
        </p>
      </div>

      {configuracionActual && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>
            Buzón configurado: <strong>{configuracionActual.usuario}</strong>
            {" — "}
            {configuracionActual.activo ? "activo" : "inactivo"}
          </span>
        </div>
      )}

      <div className="rounded-lg border border-nova-border bg-nova-panel p-5">
        <div className="mb-4 flex gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <p>
            Si el proveedor de correo exige verificación en dos pasos (Gmail, Outlook), la contraseña debe ser una
            "contraseña de aplicación" generada para NOVA — no la contraseña normal de la cuenta.
          </p>
        </div>

        <div className="mb-3 grid grid-cols-3 gap-3">
          <div className="col-span-2">
            <label className="mb-1 block text-xs text-gray-400">Servidor IMAP</label>
            <input
              value={host}
              onChange={(e) => setHost(e.target.value)}
              placeholder="imap.gmail.com"
              className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-400">Puerto</label>
            <input
              type="number"
              value={puerto}
              onChange={(e) => setPuerto(Number(e.target.value))}
              className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
            />
          </div>
        </div>

        <div className="mb-3">
          <label className="mb-1 block text-xs text-gray-400">Correo del buzón a vigilar</label>
          <input
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
            placeholder="facturas@tuempresa.co"
            className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
          />
        </div>

        <div className="mb-3">
          <label className="mb-1 block text-xs text-gray-400">
            Contraseña{configuracionActual && " (deja vacío para mantener la actual)"}
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
          />
        </div>

        <div className="mb-4">
          <label className="mb-1 block text-xs text-gray-400">Carpeta a revisar</label>
          <input
            value={carpeta}
            onChange={(e) => setCarpeta(e.target.value)}
            className="w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
          />
        </div>

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
    </div>
  );
}
