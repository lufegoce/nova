"""
Parseo de facturas electrónicas XML (formato UBL 2.1 usado por la DIAN Colombia).

El Agente Receptor usa este módulo para extraer los campos estructurales
antes de pasar el documento al enriquecimiento con LLM.
"""
from dataclasses import dataclass
from datetime import datetime

from lxml import etree

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "inv": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
}


@dataclass
class FacturaExtraida:
    nit_emisor: str
    razon_social_emisor: str | None
    numero_factura: str | None
    fecha_emision: datetime | None
    total: float
    items: list[dict]


class XMLParseError(Exception):
    pass


def parsear_factura_xml(contenido: bytes) -> FacturaExtraida:
    """
    Extrae NIT, fecha, total e ítems de un XML de factura electrónica UBL.
    Lanza XMLParseError si el documento no tiene la estructura mínima esperada.
    """
    try:
        root = etree.fromstring(contenido)
    except etree.XMLSyntaxError as exc:
        raise XMLParseError(f"XML mal formado: {exc}") from exc

    def find_text(xpath: str) -> str | None:
        el = root.find(xpath, namespaces=NS)
        return el.text.strip() if el is not None and el.text else None

    nit = find_text(
        ".//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID"
    ) or find_text(".//cac:AccountingSupplierParty//cbc:CompanyID")

    if not nit:
        raise XMLParseError("No se encontró el NIT del emisor en el XML")

    razon_social = find_text(
        ".//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name"
    ) or find_text(".//cac:AccountingSupplierParty//cbc:RegistrationName")

    numero_factura = find_text(".//cbc:ID")

    fecha_texto = find_text(".//cbc:IssueDate")
    fecha_emision = None
    if fecha_texto:
        try:
            fecha_emision = datetime.strptime(fecha_texto, "%Y-%m-%d")
        except ValueError:
            fecha_emision = None

    total_texto = find_text(".//cac:LegalMonetaryTotal/cbc:PayableAmount") or "0"
    try:
        total = float(total_texto)
    except ValueError:
        total = 0.0

    items = []
    for line in root.findall(".//cac:InvoiceLine", namespaces=NS):
        descripcion = line.findtext(".//cbc:Description", namespaces=NS)
        cantidad = line.findtext(".//cbc:InvoicedQuantity", namespaces=NS)
        valor = line.findtext(".//cbc:LineExtensionAmount", namespaces=NS)
        items.append({
            "descripcion": descripcion,
            "cantidad": float(cantidad) if cantidad else None,
            "valor": float(valor) if valor else None,
        })

    return FacturaExtraida(
        nit_emisor=nit,
        razon_social_emisor=razon_social,
        numero_factura=numero_factura,
        fecha_emision=fecha_emision,
        total=total,
        items=items,
    )
