/**
 * Cliente de la API de NOVA. TENANT_ID fijo en "demo" para el MVP;
 * en producción vendría de la sesión autenticada del usuario.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export const TENANT_ID = "demo";

export type EstadoDocumento =
  | "nuevo"
  | "validado"
  | "causado"
  | "aprobacion_pendiente"
  | "pagado"
  | "con_error"
  | "rechazado";

export interface DocumentoFinanciero {
  id: string;
  tipo: string;
  estado: EstadoDocumento;
  nit_emisor: string;
  razon_social_emisor: string | null;
  numero_factura: string | null;
  fecha_emision: string | null;
  total: number;
  cuenta_puc_sugerida: string | null;
  retenciones: Record<string, any> | null;
  origen_canal: string;
  tiene_pdf: boolean;
  erp_estado: "no_configurado" | "enviado" | "error";
  erp_referencia: string | null;
  erp_detalle_error: string | null;
  creado_en: string;
  actualizado_en: string;
}

export interface EventoAuditoria {
  id: string;
  agente: string;
  accion: string;
  detalle: string | null;
  resultado: Record<string, any> | null;
  creado_en: string;
}

export interface DocumentoDianListado {
  id: string;
  cufe: string;
  nit_emisor: string | null;
  razon_social_emisor: string | null;
  numero_documento: string | null;
  fecha_emision: string | null;
  total: string | null;
  estado_descarga: "pendiente" | "descargado";
  documento_financiero_id: string | null;
  visto_en: string;
}

function headers() {
  return { "X-Tenant-Id": TENANT_ID, "Content-Type": "application/json" };
}

async function manejarError(res: Response, mensajePorDefecto: string) {
  if (res.ok) return;
  let detalle = mensajePorDefecto;
  try {
    detalle = (await res.json()).detail ?? mensajePorDefecto;
  } catch {
    // el cuerpo no era JSON; se usa el mensaje por defecto
  }
  throw new Error(detalle);
}

export async function listarFacturas(): Promise<DocumentoFinanciero[]> {
  const res = await fetch(`${API_BASE}/facturas`, { headers: headers(), cache: "no-store" });
  await manejarError(res, "Error al listar facturas");
  return res.json();
}

export async function obtenerTrazabilidad(documentoId: string): Promise<EventoAuditoria[]> {
  const res = await fetch(`${API_BASE}/facturas/${documentoId}/trazabilidad`, {
    headers: headers(),
    cache: "no-store",
  });
  await manejarError(res, "Error al obtener trazabilidad");
  return res.json();
}

export async function aprobarFactura(
  documentoId: string,
  aprobado: boolean,
  aprobadoPor: string,
  comentario?: string,
  cuentaPucCorregida?: string
): Promise<DocumentoFinanciero> {
  const res = await fetch(`${API_BASE}/facturas/${documentoId}/aprobar`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      aprobado,
      aprobado_por: aprobadoPor,
      comentario,
      cuenta_puc_corregida: cuentaPucCorregida,
    }),
  });
  await manejarError(res, "Error al aprobar factura");
  return res.json();
}

export interface DatosIngestaPdf {
  archivo: File;
  nitEmisor: string;
  total: number;
  razonSocialEmisor?: string;
  numeroFactura?: string;
  fechaEmision?: string;
  cufe?: string;
}

export async function ingestarFacturaPdf(datos: DatosIngestaPdf): Promise<DocumentoFinanciero> {
  const formData = new FormData();
  formData.append("archivo", datos.archivo);
  formData.append("nit_emisor", datos.nitEmisor);
  formData.append("total", String(datos.total));
  if (datos.razonSocialEmisor) formData.append("razon_social_emisor", datos.razonSocialEmisor);
  if (datos.numeroFactura) formData.append("numero_factura", datos.numeroFactura);
  if (datos.fechaEmision) formData.append("fecha_emision", datos.fechaEmision);
  if (datos.cufe) formData.append("cufe", datos.cufe);

  const res = await fetch(`${API_BASE}/facturas/ingesta-pdf`, {
    method: "POST",
    headers: { "X-Tenant-Id": TENANT_ID },
    body: formData,
  });
  await manejarError(res, "Error al subir la factura en PDF");
  return res.json();
}

export function urlPdfFactura(documentoId: string): string {
  return `${API_BASE}/facturas/${documentoId}/pdf`;
}

/**
 * El endpoint de PDF requiere el header X-Tenant-Id, que un <iframe src="..."> o
 * <img src="..."> no puede enviar. Por eso se trae con fetch() y se expone como
 * blob URL para usar en el iframe de previsualización.
 */
export async function obtenerPdfBlobUrl(documentoId: string): Promise<string> {
  const res = await fetch(urlPdfFactura(documentoId), { headers: headers() });
  await manejarError(res, "No se pudo cargar el PDF");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function vincularSesionDian(magicLinkUrl: string): Promise<{ nit_vinculado: string | null }> {
  const res = await fetch(`${API_BASE}/dian/vincular`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ magic_link_url: magicLinkUrl }),
  });
  await manejarError(res, "No se pudo vincular la sesión DIAN");
  return res.json();
}

export async function obtenerSesionDian(): Promise<{ nit_vinculado: string | null } | null> {
  const res = await fetch(`${API_BASE}/dian/sesion`, { headers: headers(), cache: "no-store" });
  if (res.status === 404) return null;
  await manejarError(res, "Error al consultar la sesión DIAN");
  return res.json();
}

export async function listarDocumentosDian(): Promise<DocumentoDianListado[]> {
  const res = await fetch(`${API_BASE}/dian/documentos-recibidos`, { headers: headers(), cache: "no-store" });
  await manejarError(res, "Error al listar documentos de la DIAN");
  return res.json();
}

export async function obtenerUrlPortalDian(): Promise<string> {
  const res = await fetch(`${API_BASE}/dian/portal-url`, { headers: headers(), cache: "no-store" });
  await manejarError(res, "Error al obtener la URL del portal DIAN");
  return (await res.json()).url;
}

export type TipoErp =
  | "siigo"
  | "odoo"
  | "sap_business_one"
  | "alegra"
  | "loggro"
  | "contapyme"
  | "siesa"
  | "defontana";

export interface ConfiguracionErp {
  tipo_erp: TipoErp;
  activo: boolean;
  creado_en: string;
  actualizado_en: string;
  campos_configurados: string[];
}

export async function obtenerConfiguracionErp(): Promise<ConfiguracionErp | null> {
  const res = await fetch(`${API_BASE}/configuracion/erp`, { headers: headers(), cache: "no-store" });
  if (res.status === 404) return null;
  await manejarError(res, "Error al consultar la configuración de ERP");
  return res.json();
}

export async function guardarConfiguracionErp(
  tipoErp: TipoErp,
  credenciales: Record<string, string | boolean>,
  activo: boolean
): Promise<ConfiguracionErp> {
  const res = await fetch(`${API_BASE}/configuracion/erp`, {
    method: "PUT",
    headers: headers(),
    body: JSON.stringify({ tipo_erp: tipoErp, credenciales, activo }),
  });
  await manejarError(res, "Error al guardar la configuración de ERP");
  return res.json();
}

export type SeveridadAlerta = "baja" | "media" | "alta";

export interface AlertaSeguridad {
  id: string;
  tipo: string;
  severidad: SeveridadAlerta;
  detalle: string;
  contexto: Record<string, any> | null;
  documento_id: string | null;
  resuelta: boolean;
  creado_en: string;
}

export interface ResultadoEscaneo {
  aprobaciones_rapidas: number;
  pago_rapido_alto_valor: number;
  fallos_erp_repetidos: number;
  correcciones_puc_inestables: number;
  total_alertas_nuevas: number;
}

export async function listarAlertasSeguridad(soloNoResueltas = true): Promise<AlertaSeguridad[]> {
  const res = await fetch(`${API_BASE}/seguridad/alertas?solo_no_resueltas=${soloNoResueltas}`, {
    headers: headers(),
    cache: "no-store",
  });
  await manejarError(res, "Error al listar alertas de seguridad");
  return res.json();
}

export async function escanearSeguridadAhora(): Promise<ResultadoEscaneo> {
  const res = await fetch(`${API_BASE}/seguridad/escanear`, { method: "POST", headers: headers() });
  await manejarError(res, "Error al ejecutar el escaneo de seguridad");
  return res.json();
}

export async function resolverAlertaSeguridad(alertaId: string): Promise<AlertaSeguridad> {
  const res = await fetch(`${API_BASE}/seguridad/alertas/${alertaId}/resolver`, {
    method: "POST",
    headers: headers(),
  });
  await manejarError(res, "Error al resolver la alerta");
  return res.json();
}

export function conectarWebSocket(onMensaje: (data: any) => void): WebSocket {
  const wsBase = (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000").replace(/^http/, "ws");
  const ws = new WebSocket(`${wsBase}/ws/${TENANT_ID}`);
  ws.onmessage = (event) => onMensaje(JSON.parse(event.data));
  return ws;
}
