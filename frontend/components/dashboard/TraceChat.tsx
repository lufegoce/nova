"use client";

import { useState } from "react";
import { MessageCircle, Send } from "lucide-react";
import type { DocumentoFinanciero } from "@/lib/api";
import { obtenerTrazabilidad } from "@/lib/api";

interface Mensaje {
  autor: "usuario" | "nova";
  texto: string;
}

interface Props {
  documentos: DocumentoFinanciero[];
}

/**
 * Chat Inteligente de trazabilidad. En este MVP interpreta la pregunta con
 * una heurística simple (busca el número de factura mencionado) y responde
 * reconstruyendo la cadena de eventos de auditoría. El reemplazo natural en
 * producción es enrutar la pregunta a un agente con RAG sobre EventoAuditoria.
 */
export function TraceChat({ documentos }: Props) {
  const [mensajes, setMensajes] = useState<Mensaje[]>([
    { autor: "nova", texto: "Pregúntame por ejemplo: ¿por qué no se ha pagado la factura FE-1002?" },
  ]);
  const [input, setInput] = useState("");
  const [cargando, setCargando] = useState(false);

  async function enviar() {
    const pregunta = input.trim();
    if (!pregunta) return;
    setInput("");
    setMensajes((m) => [...m, { autor: "usuario", texto: pregunta }]);
    setCargando(true);

    const numeroMencionado = documentos.find((d) =>
      d.numero_factura && pregunta.toLowerCase().includes(d.numero_factura.toLowerCase())
    );

    if (!numeroMencionado) {
      setMensajes((m) => [
        ...m,
        { autor: "nova", texto: "No encontré esa factura en los documentos del tenant actual." },
      ]);
      setCargando(false);
      return;
    }

    try {
      const eventos = await obtenerTrazabilidad(numeroMencionado.id);
      const resumen =
        eventos.length === 0
          ? "Aún no hay eventos registrados para este documento."
          : eventos
              .map((e) => `• [${e.agente}] ${e.accion}${e.detalle ? `: ${e.detalle}` : ""}`)
              .join("\n");

      setMensajes((m) => [
        ...m,
        {
          autor: "nova",
          texto: `Estado actual: ${numeroMencionado.estado}.\n\nTrazabilidad:\n${resumen}`,
        },
      ]);
    } catch {
      setMensajes((m) => [...m, { autor: "nova", texto: "No pude consultar la trazabilidad en este momento." }]);
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-nova-border bg-nova-panel">
      <div className="flex items-center gap-2 border-b border-nova-border p-3">
        <MessageCircle className="h-4 w-4 text-nova-accent" />
        <span className="text-sm font-medium">Chat de trazabilidad</span>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-3 text-sm">
        {mensajes.map((m, i) => (
          <div
            key={i}
            className={
              m.autor === "usuario"
                ? "ml-auto max-w-[85%] whitespace-pre-wrap rounded-lg bg-nova-accent/20 p-2 text-right"
                : "mr-auto max-w-[85%] whitespace-pre-wrap rounded-lg bg-nova-bg p-2"
            }
          >
            {m.texto}
          </div>
        ))}
        {cargando && <div className="text-xs text-gray-500">NOVA está consultando la auditoría...</div>}
      </div>

      <div className="flex gap-2 border-t border-nova-border p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && enviar()}
          placeholder="Escribe tu pregunta..."
          className="flex-1 rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-sm outline-none focus:border-nova-accent"
        />
        <button
          onClick={enviar}
          className="rounded-lg bg-nova-accent px-3 py-2 text-white hover:bg-blue-600"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
