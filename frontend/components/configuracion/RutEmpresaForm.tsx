"use client";

import { useState } from "react";
import { FileUp, Sparkles } from "lucide-react";
import { crearEmpresaContador, extraerDatosRut, type Empresa } from "@/lib/api";

interface Props {
  onCreada: (empresa: Empresa) => void;
}

interface CamposEmpresa {
  nombre: string;
  nit: string;
  digitoVerificacion: string;
  tipoPersona: string;
  actividadEconomicaCodigo: string;
  actividadEconomicaDescripcion: string;
  direccion: string;
  departamento: string;
  municipio: string;
  correoElectronico: string;
  telefono: string;
  representanteLegalNombre: string;
  representanteLegalIdentificacion: string;
  estadoRut: string;
}

const CAMPOS_VACIOS: CamposEmpresa = {
  nombre: "",
  nit: "",
  digitoVerificacion: "",
  tipoPersona: "",
  actividadEconomicaCodigo: "",
  actividadEconomicaDescripcion: "",
  direccion: "",
  departamento: "",
  municipio: "",
  correoElectronico: "",
  telefono: "",
  representanteLegalNombre: "",
  representanteLegalIdentificacion: "",
  estadoRut: "",
};

/**
 * Creación de empresa por el contador. Se puede adjuntar el RUT en PDF: la IA
 * propone los campos (Claude lee el PDF directamente) y el contador los
 * revisa/corrige aquí antes de crear la empresa — nunca se guarda sin que un
 * humano confirme los datos.
 */
export function RutEmpresaForm({ onCreada }: Props) {
  const [archivoRut, setArchivoRut] = useState<File | null>(null);
  const [extrayendo, setExtrayendo] = useState(false);
  const [avisoExtraccion, setAvisoExtraccion] = useState<string | null>(null);
  const [campos, setCampos] = useState<CamposEmpresa>(CAMPOS_VACIOS);
  const [creando, setCreando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandido, setExpandido] = useState(false);

  function actualizar<K extends keyof CamposEmpresa>(campo: K, valor: string) {
    setCampos((prev) => ({ ...prev, [campo]: valor }));
  }

  async function extraer() {
    if (!archivoRut) return;
    setExtrayendo(true);
    setAvisoExtraccion(null);
    setError(null);
    try {
      const propuesta = await extraerDatosRut(archivoRut);
      if (!propuesta.extraido_automaticamente) {
        setAvisoExtraccion(propuesta.razon ?? "No se pudo extraer automáticamente; diligencia los campos.");
      } else {
        setAvisoExtraccion("Datos leídos del RUT. Revísalos antes de crear la empresa.");
      }
      setCampos({
        nombre: propuesta.nombre ?? "",
        nit: propuesta.nit ?? "",
        digitoVerificacion: propuesta.digito_verificacion ?? "",
        tipoPersona: propuesta.tipo_persona ?? "",
        actividadEconomicaCodigo: propuesta.actividad_economica_codigo ?? "",
        actividadEconomicaDescripcion: propuesta.actividad_economica_descripcion ?? "",
        direccion: propuesta.direccion ?? "",
        departamento: propuesta.departamento ?? "",
        municipio: propuesta.municipio ?? "",
        correoElectronico: propuesta.correo_electronico ?? "",
        telefono: propuesta.telefono ?? "",
        representanteLegalNombre: propuesta.representante_legal_nombre ?? "",
        representanteLegalIdentificacion: propuesta.representante_legal_identificacion ?? "",
        estadoRut: propuesta.estado_rut ?? "",
      });
      setExpandido(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo leer el RUT");
    } finally {
      setExtrayendo(false);
    }
  }

  async function crear(e: React.FormEvent) {
    e.preventDefault();
    if (!campos.nombre) {
      setError("El nombre de la empresa es obligatorio");
      return;
    }
    setCreando(true);
    setError(null);
    try {
      const empresa = await crearEmpresaContador({
        nombre: campos.nombre,
        nit: campos.nit || undefined,
        digitoVerificacion: campos.digitoVerificacion || undefined,
        tipoPersona: campos.tipoPersona || undefined,
        actividadEconomicaCodigo: campos.actividadEconomicaCodigo || undefined,
        actividadEconomicaDescripcion: campos.actividadEconomicaDescripcion || undefined,
        direccion: campos.direccion || undefined,
        departamento: campos.departamento || undefined,
        municipio: campos.municipio || undefined,
        correoElectronico: campos.correoElectronico || undefined,
        telefono: campos.telefono || undefined,
        representanteLegalNombre: campos.representanteLegalNombre || undefined,
        representanteLegalIdentificacion: campos.representanteLegalIdentificacion || undefined,
        estadoRut: campos.estadoRut || undefined,
        archivoRut: archivoRut ?? undefined,
      });
      onCreada(empresa);
      setCampos(CAMPOS_VACIOS);
      setArchivoRut(null);
      setAvisoExtraccion(null);
      setExpandido(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al crear la empresa");
    } finally {
      setCreando(false);
    }
  }

  return (
    <div className="rounded-lg border border-nova-border bg-nova-panel p-4">
      <h2 className="mb-1 text-sm font-semibold">Nueva empresa</h2>
      <p className="mb-3 text-xs text-gray-500">
        Adjunta el RUT en PDF para que NOVA proponga los datos, o diligencia el formulario manualmente.
      </p>

      <div className="mb-3 flex items-center gap-2">
        <input
          type="file"
          accept="application/pdf,.pdf"
          onChange={(e) => setArchivoRut(e.target.files?.[0] ?? null)}
          className="flex-1 rounded-lg border border-nova-border bg-nova-bg p-2 text-xs"
        />
        <button
          type="button"
          onClick={extraer}
          disabled={!archivoRut || extrayendo}
          className="flex items-center gap-1.5 rounded-lg bg-nova-accent px-3 py-2 text-xs font-medium text-white hover:bg-blue-600 disabled:opacity-50"
        >
          <Sparkles className="h-3.5 w-3.5" />
          {extrayendo ? "Leyendo RUT..." : "Extraer datos"}
        </button>
      </div>

      {avisoExtraccion && <p className="mb-3 text-xs text-amber-300">{avisoExtraccion}</p>}

      {!expandido && (
        <button
          type="button"
          onClick={() => setExpandido(true)}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-nova-accent"
        >
          <FileUp className="h-3.5 w-3.5" />
          O diligencia el formulario manualmente
        </button>
      )}

      {expandido && (
        <form onSubmit={crear} className="mt-2 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Razón social / nombre *</label>
              <input
                required
                value={campos.nombre}
                onChange={(e) => actualizar("nombre", e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="col-span-2">
                <label className="mb-1 block text-xs text-gray-400">NIT</label>
                <input
                  value={campos.nit}
                  onChange={(e) => actualizar("nit", e.target.value)}
                  className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-400">DV</label>
                <input
                  value={campos.digitoVerificacion}
                  onChange={(e) => actualizar("digitoVerificacion", e.target.value)}
                  className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Tipo de persona</label>
              <select
                value={campos.tipoPersona}
                onChange={(e) => actualizar("tipoPersona", e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              >
                <option value="">—</option>
                <option value="natural">Natural</option>
                <option value="juridica">Jurídica</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Código CIIU</label>
              <input
                value={campos.actividadEconomicaCodigo}
                onChange={(e) => actualizar("actividadEconomicaCodigo", e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Estado del RUT</label>
              <input
                value={campos.estadoRut}
                onChange={(e) => actualizar("estadoRut", e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs text-gray-400">Actividad económica</label>
            <input
              value={campos.actividadEconomicaDescripcion}
              onChange={(e) => actualizar("actividadEconomicaDescripcion", e.target.value)}
              className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Dirección</label>
              <input
                value={campos.direccion}
                onChange={(e) => actualizar("direccion", e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Departamento</label>
              <input
                value={campos.departamento}
                onChange={(e) => actualizar("departamento", e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Municipio</label>
              <input
                value={campos.municipio}
                onChange={(e) => actualizar("municipio", e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Correo electrónico</label>
              <input
                value={campos.correoElectronico}
                onChange={(e) => actualizar("correoElectronico", e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Teléfono</label>
              <input
                value={campos.telefono}
                onChange={(e) => actualizar("telefono", e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Representante legal</label>
              <input
                value={campos.representanteLegalNombre}
                onChange={(e) => actualizar("representanteLegalNombre", e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Identificación representante legal</label>
              <input
                value={campos.representanteLegalIdentificacion}
                onChange={(e) => actualizar("representanteLegalIdentificacion", e.target.value)}
                className="w-full rounded-lg border border-nova-border bg-nova-bg p-2 text-sm outline-none focus:border-nova-accent"
              />
            </div>
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setExpandido(false)}
              className="rounded-lg border border-nova-border px-4 py-2 text-sm text-gray-300 hover:bg-nova-bg"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={creando}
              className="rounded-lg bg-nova-accent px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
            >
              {creando ? "Creando..." : "Crear empresa"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
