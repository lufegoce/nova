"use client";

import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { vincularSesionDian } from "@/lib/api";

interface Props {
  onCerrar: () => void;
  onVinculado: () => void;
}

/**
 * Modal para vincular la sesión DIAN pegando el magic-link que llega al
 * correo. El link contiene un token de sesión real y de un solo uso — se
 * envía directo al backend, nunca se guarda en el estado del cliente más
 * tiempo del necesario ni se registra en ningún log del navegador.
 */
export function LinkDianModal({ onCerrar, onVinculado }: Props) {
  const [magicLink, setMagicLink] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function vincular() {
    if (!magicLink.trim()) return;
    setEnviando(true);
    setError(null);
    try {
      await vincularSesionDian(magicLink.trim());
      onVinculado();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error inesperado al vincular la sesión");
    } finally {
      setEnviando(false);
      setMagicLink("");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded-xl border border-nova-border bg-nova-panel p-6">
        <div className="mb-4 flex items-start justify-between">
          <h3 className="text-lg font-semibold">Vincular sesión DIAN</h3>
          <button onClick={onCerrar} className="text-gray-500 hover:text-gray-300">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mb-4 flex gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <p>
            Ese enlace es una credencial real de tu cuenta DIAN, generalmente de un solo uso.
            Pégalo solo aquí, no lo compartas en otro lugar. Después de vincular, NOVA solo
            usa la sesión para listar documentos — nunca descarga archivos automáticamente.
          </p>
        </div>

        <label className="mb-1 block text-xs text-gray-400">
          Enlace recibido en el correo de la DIAN
        </label>
        <input
          value={magicLink}
          onChange={(e) => setMagicLink(e.target.value)}
          placeholder="https://catalogo-vpfe.dian.gov.co/User/AuthToken?..."
          className="mb-4 w-full rounded-lg border border-nova-border bg-nova-bg p-3 text-sm outline-none focus:border-nova-accent"
        />

        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-3">
          <button
            onClick={onCerrar}
            className="rounded-lg border border-nova-border px-4 py-2 text-sm text-gray-300 hover:bg-nova-bg"
          >
            Cancelar
          </button>
          <button
            disabled={enviando || !magicLink.trim()}
            onClick={vincular}
            className="rounded-lg bg-nova-accent px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
          >
            {enviando ? "Vinculando..." : "Vincular"}
          </button>
        </div>
      </div>
    </div>
  );
}
