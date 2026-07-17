/**
 * Cliente de la API de NOVA. El tenant activo ya no se fija en el cliente:
 * lo resuelve el backend a partir de la cookie de sesión httpOnly emitida en
 * el login (ver app/api/deps.py y app/api/routes/auth.py). Todas las
 * llamadas van con credentials: "include" para que esa cookie viaje.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

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
  return { "Content-Type": "application/json" };
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function manejarError(res: Response, mensajePorDefecto: string) {
  if (res.ok) return;
  let detalle = mensajePorDefecto;
  try {
    detalle = (await res.json()).detail ?? mensajePorDefecto;
  } catch {
    // el cuerpo no era JSON; se usa el mensaje por defecto
  }
  throw new ApiError(res.status, detalle);
}

// ---------------------------------------------------------------------------
// Autenticación
// ---------------------------------------------------------------------------

export type RolUsuario = "contador" | "empresa";

export interface EmpresaActual {
  id: string;
  nombre: string;
  tenant_id: string;
}

export interface SesionActual {
  rol: RolUsuario;
  nombre: string;
  email: string;
  empresa_actual: EmpresaActual | null;
}

export interface ResponsabilidadTributaria {
  codigo: string;
  descripcion: string;
}

export interface Empresa {
  id: string;
  nombre: string;
  nit: string | null;
  tenant_id: string;
  digito_verificacion: string | null;
  tipo_persona: string | null;
  responsabilidades_tributarias: ResponsabilidadTributaria[] | null;
  actividad_economica_codigo: string | null;
  actividad_economica_descripcion: string | null;
  direccion: string | null;
  departamento: string | null;
  municipio: string | null;
  correo_electronico: string | null;
  telefono: string | null;
  representante_legal_nombre: string | null;
  representante_legal_identificacion: string | null;
  estado_rut: string | null;
  tiene_rut: boolean;
  creado_en: string;
}

export interface RutExtraido {
  extraido_automaticamente: boolean;
  razon: string | null;
  nombre: string | null;
  nit: string | null;
  digito_verificacion: string | null;
  tipo_persona: string | null;
  responsabilidades_tributarias: ResponsabilidadTributaria[] | null;
  actividad_economica_codigo: string | null;
  actividad_economica_descripcion: string | null;
  direccion: string | null;
  departamento: string | null;
  municipio: string | null;
  correo_electronico: string | null;
  telefono: string | null;
  representante_legal_nombre: string | null;
  representante_legal_identificacion: string | null;
  estado_rut: string | null;
}

export interface DatosEmpresaFormulario {
  nombre: string;
  nit?: string;
  digitoVerificacion?: string;
  tipoPersona?: string;
  responsabilidadesTributarias?: ResponsabilidadTributaria[];
  actividadEconomicaCodigo?: string;
  actividadEconomicaDescripcion?: string;
  direccion?: string;
  departamento?: string;
  municipio?: string;
  correoElectronico?: string;
  telefono?: string;
  representanteLegalNombre?: string;
  representanteLegalIdentificacion?: string;
  estadoRut?: string;
  archivoRut?: File;
}

export type RolUsuarioEmpresa = "administrador" | "aprobador" | "operador" | "consulta";

export interface UsuarioEmpresa {
  id: string;
  empresa_id: string;
  email: string;
  nombre: string;
  telefono: string | null;
  rol: RolUsuarioEmpresa;
  activo: boolean;
  creado_en: string;
}

async function login(ruta: "contador" | "empresa", email: string, password: string): Promise<SesionActual> {
  const res = await fetch(`${API_BASE}/auth/login/${ruta}`, {
    method: "POST",
    headers: headers(),
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  await manejarError(res, "Email o contraseña incorrectos");
  return res.json();
}

export const loginContador = (email: string, password: string) => login("contador", email, password);
export const loginEmpresa = (email: string, password: string) => login("empresa", email, password);

export async function cerrarSesion(): Promise<void> {
  await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" });
}

export async function obtenerSesionActual(): Promise<SesionActual | null> {
  const res = await fetch(`${API_BASE}/auth/me`, { credentials: "include", cache: "no-store" });
  if (res.status === 401) return null;
  await manejarError(res, "Error al consultar la sesión");
  return res.json();
}

export async function listarEmpresasContador(): Promise<Empresa[]> {
  const res = await fetch(`${API_BASE}/auth/empresas`, { credentials: "include", cache: "no-store" });
  await manejarError(res, "Error al listar empresas");
  return res.json();
}

export async function extraerDatosRut(archivo: File): Promise<RutExtraido> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  const res = await fetch(`${API_BASE}/auth/empresas/extraer-rut`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  await manejarError(res, "No se pudo leer el RUT");
  return res.json();
}

export async function crearEmpresaContador(datos: DatosEmpresaFormulario): Promise<Empresa> {
  const formData = new FormData();
  formData.append("nombre", datos.nombre);
  if (datos.nit) formData.append("nit", datos.nit);
  if (datos.digitoVerificacion) formData.append("digito_verificacion", datos.digitoVerificacion);
  if (datos.tipoPersona) formData.append("tipo_persona", datos.tipoPersona);
  if (datos.responsabilidadesTributarias) {
    formData.append("responsabilidades_tributarias", JSON.stringify(datos.responsabilidadesTributarias));
  }
  if (datos.actividadEconomicaCodigo) formData.append("actividad_economica_codigo", datos.actividadEconomicaCodigo);
  if (datos.actividadEconomicaDescripcion) {
    formData.append("actividad_economica_descripcion", datos.actividadEconomicaDescripcion);
  }
  if (datos.direccion) formData.append("direccion", datos.direccion);
  if (datos.departamento) formData.append("departamento", datos.departamento);
  if (datos.municipio) formData.append("municipio", datos.municipio);
  if (datos.correoElectronico) formData.append("correo_electronico", datos.correoElectronico);
  if (datos.telefono) formData.append("telefono", datos.telefono);
  if (datos.representanteLegalNombre) formData.append("representante_legal_nombre", datos.representanteLegalNombre);
  if (datos.representanteLegalIdentificacion) {
    formData.append("representante_legal_identificacion", datos.representanteLegalIdentificacion);
  }
  if (datos.estadoRut) formData.append("estado_rut", datos.estadoRut);
  if (datos.archivoRut) formData.append("archivo_rut", datos.archivoRut);

  const res = await fetch(`${API_BASE}/auth/empresas`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  await manejarError(res, "Error al crear la empresa");
  return res.json();
}

export async function seleccionarEmpresa(empresaId: string): Promise<SesionActual> {
  const res = await fetch(`${API_BASE}/auth/empresas/${empresaId}/seleccionar`, {
    method: "POST",
    credentials: "include",
  });
  await manejarError(res, "Error al seleccionar la empresa");
  return res.json();
}

export async function listarUsuariosEmpresa(empresaId: string): Promise<UsuarioEmpresa[]> {
  const res = await fetch(`${API_BASE}/auth/empresas/${empresaId}/usuarios`, {
    credentials: "include",
    cache: "no-store",
  });
  await manejarError(res, "Error al listar usuarios de la empresa");
  return res.json();
}

export async function crearUsuarioEmpresa(
  empresaId: string,
  datos: { email: string; password: string; nombre: string; rol: RolUsuarioEmpresa; telefono?: string }
): Promise<UsuarioEmpresa> {
  const res = await fetch(`${API_BASE}/auth/empresas/${empresaId}/usuarios`, {
    method: "POST",
    headers: headers(),
    credentials: "include",
    body: JSON.stringify(datos),
  });
  await manejarError(res, "Error al crear el usuario");
  return res.json();
}

// ---------------------------------------------------------------------------
// Documentos financieros
// ---------------------------------------------------------------------------

export async function listarFacturas(): Promise<DocumentoFinanciero[]> {
  const res = await fetch(`${API_BASE}/facturas`, { headers: headers(), credentials: "include", cache: "no-store" });
  await manejarError(res, "Error al listar facturas");
  return res.json();
}

export async function obtenerTrazabilidad(documentoId: string): Promise<EventoAuditoria[]> {
  const res = await fetch(`${API_BASE}/facturas/${documentoId}/trazabilidad`, {
    headers: headers(),
    credentials: "include",
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
    credentials: "include",
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

export interface DatosFacturaExtraidos {
  extraido_automaticamente: boolean;
  razon: string | null;
  nit_emisor: string | null;
  razon_social_emisor: string | null;
  numero_factura: string | null;
  fecha_emision: string | null;
  total: number | null;
  cufe: string | null;
}

export async function extraerDatosFacturaPdf(archivo: File): Promise<DatosFacturaExtraidos> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  const res = await fetch(`${API_BASE}/facturas/extraer-datos-pdf`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  await manejarError(res, "No se pudo leer la factura");
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
    credentials: "include",
    body: formData,
  });
  await manejarError(res, "Error al subir la factura en PDF");
  return res.json();
}

export function urlPdfFactura(documentoId: string): string {
  return `${API_BASE}/facturas/${documentoId}/pdf`;
}

/**
 * El endpoint de PDF requiere la cookie de sesión, que un <iframe src="..."> o
 * <img src="..."> no envía de forma confiable entre orígenes. Por eso se trae
 * con fetch() (credentials: "include") y se expone como blob URL para el iframe.
 */
export async function obtenerPdfBlobUrl(documentoId: string): Promise<string> {
  const res = await fetch(urlPdfFactura(documentoId), { headers: headers(), credentials: "include" });
  await manejarError(res, "No se pudo cargar el PDF");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export interface SesionDian {
  nit_vinculado: string | null;
  vinculado_en: string;
  actualizado_en: string;
}

export async function vincularSesionDian(magicLinkUrl: string): Promise<SesionDian> {
  const res = await fetch(`${API_BASE}/dian/vincular`, {
    method: "POST",
    headers: headers(),
    credentials: "include",
    body: JSON.stringify({ magic_link_url: magicLinkUrl }),
  });
  await manejarError(res, "No se pudo vincular la sesión DIAN");
  return res.json();
}

export async function obtenerSesionDian(): Promise<SesionDian | null> {
  const res = await fetch(`${API_BASE}/dian/sesion`, { headers: headers(), credentials: "include", cache: "no-store" });
  if (res.status === 404) return null;
  await manejarError(res, "Error al consultar la sesión DIAN");
  return res.json();
}

export interface FiltrosDocumentosDian {
  fechaInicio?: string; // YYYY-MM-DD
  fechaFin?: string; // YYYY-MM-DD
}

export async function listarDocumentosDian(
  filtros: FiltrosDocumentosDian = {}
): Promise<DocumentoDianListado[]> {
  const params = new URLSearchParams();
  if (filtros.fechaInicio) params.set("fecha_inicio", filtros.fechaInicio);
  if (filtros.fechaFin) params.set("fecha_fin", filtros.fechaFin);
  const query = params.toString();

  const res = await fetch(`${API_BASE}/dian/documentos-recibidos${query ? `?${query}` : ""}`, {
    headers: headers(),
    credentials: "include",
    cache: "no-store",
  });
  await manejarError(res, "Error al listar documentos de la DIAN");
  return res.json();
}

export async function obtenerUrlPortalDian(): Promise<string> {
  const res = await fetch(`${API_BASE}/dian/portal-url`, { headers: headers(), credentials: "include", cache: "no-store" });
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
  const res = await fetch(`${API_BASE}/configuracion/erp`, { headers: headers(), credentials: "include", cache: "no-store" });
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
    credentials: "include",
    body: JSON.stringify({ tipo_erp: tipoErp, credenciales, activo }),
  });
  await manejarError(res, "Error al guardar la configuración de ERP");
  return res.json();
}

// ---------------------------------------------------------------------------
// PST (Proveedor de Servicios Tecnológicos DIAN) — recepción de documentos
// sin captcha, vía la API oficial del PST en vez del portal humano.
// ---------------------------------------------------------------------------

export type TipoPst = "factus";

export interface ConfiguracionPst {
  tipo_pst: TipoPst;
  activo: boolean;
  creado_en: string;
  actualizado_en: string;
  campos_configurados: string[];
}

export interface DocumentoRecibidoPst {
  cufe: string;
  nit_emisor: string | null;
  razon_social_emisor: string | null;
  numero_documento: string | null;
  fecha_emision: string | null;
  tiene_eventos_pendientes: boolean | null;
}

export async function obtenerConfiguracionPst(): Promise<ConfiguracionPst | null> {
  const res = await fetch(`${API_BASE}/configuracion/pst`, { headers: headers(), credentials: "include", cache: "no-store" });
  if (res.status === 404) return null;
  await manejarError(res, "Error al consultar la configuración del PST");
  return res.json();
}

export async function guardarConfiguracionPst(
  tipoPst: TipoPst,
  credenciales: Record<string, string | boolean>,
  activo: boolean
): Promise<ConfiguracionPst> {
  const res = await fetch(`${API_BASE}/configuracion/pst`, {
    method: "PUT",
    headers: headers(),
    credentials: "include",
    body: JSON.stringify({ tipo_pst: tipoPst, credenciales, activo }),
  });
  await manejarError(res, "Error al guardar la configuración del PST");
  return res.json();
}

export async function probarConexionPst(): Promise<void> {
  const res = await fetch(`${API_BASE}/configuracion/pst/probar`, { method: "POST", credentials: "include" });
  await manejarError(res, "No se pudo conectar con el PST");
}

export async function listarDocumentosRecibidosPst(): Promise<DocumentoRecibidoPst[]> {
  const res = await fetch(`${API_BASE}/configuracion/pst/documentos-recibidos`, {
    headers: headers(),
    credentials: "include",
    cache: "no-store",
  });
  await manejarError(res, "Error al listar documentos recibidos del PST");
  return res.json();
}

// ---------------------------------------------------------------------------
// Buzón de correo (IMAP) que NOVA vigila para recibir facturas de
// proveedores directamente por email — alternativa a subir el PDF/XML a
// mano, ver backend/app/services/correo_watcher.py. La contraseña nunca
// viaja de vuelta en la respuesta de la API, solo se envía al guardar.
// ---------------------------------------------------------------------------

export interface ConfiguracionCorreo {
  host: string;
  puerto: number;
  usuario: string;
  carpeta: string;
  activo: boolean;
  creado_en: string;
  actualizado_en: string;
}

export interface DatosConfiguracionCorreo {
  host: string;
  puerto: number;
  usuario: string;
  password: string;
  carpeta: string;
  activo: boolean;
}

export async function obtenerConfiguracionCorreo(): Promise<ConfiguracionCorreo | null> {
  const res = await fetch(`${API_BASE}/configuracion/correo`, {
    headers: headers(),
    credentials: "include",
    cache: "no-store",
  });
  if (res.status === 404) return null;
  await manejarError(res, "Error al consultar la configuración del correo");
  return res.json();
}

export async function guardarConfiguracionCorreo(datos: DatosConfiguracionCorreo): Promise<ConfiguracionCorreo> {
  const res = await fetch(`${API_BASE}/configuracion/correo`, {
    method: "PUT",
    headers: headers(),
    credentials: "include",
    body: JSON.stringify(datos),
  });
  await manejarError(res, "Error al guardar la configuración del correo");
  return res.json();
}

export async function probarConexionCorreo(): Promise<void> {
  const res = await fetch(`${API_BASE}/configuracion/correo/probar`, { method: "POST", credentials: "include" });
  await manejarError(res, "No se pudo conectar al buzón de correo");
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
    credentials: "include",
    cache: "no-store",
  });
  await manejarError(res, "Error al listar alertas de seguridad");
  return res.json();
}

export async function escanearSeguridadAhora(): Promise<ResultadoEscaneo> {
  const res = await fetch(`${API_BASE}/seguridad/escanear`, { method: "POST", headers: headers(), credentials: "include" });
  await manejarError(res, "Error al ejecutar el escaneo de seguridad");
  return res.json();
}

export async function resolverAlertaSeguridad(alertaId: string): Promise<AlertaSeguridad> {
  const res = await fetch(`${API_BASE}/seguridad/alertas/${alertaId}/resolver`, {
    method: "POST",
    headers: headers(),
    credentials: "include",
  });
  await manejarError(res, "Error al resolver la alerta");
  return res.json();
}

export function conectarWebSocket(tenantId: string, onMensaje: (data: any) => void): WebSocket {
  const wsBase = (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000").replace(/^http/, "ws");
  const ws = new WebSocket(`${wsBase}/ws/${tenantId}`);
  ws.onmessage = (event) => onMensaje(JSON.parse(event.data));
  return ws;
}
