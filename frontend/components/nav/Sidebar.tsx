"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  Bot,
  Building2,
  ChevronDown,
  FileText,
  BarChart3,
  GitCompare,
  Link2,
  Settings,
  ShieldAlert,
  Users,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

interface SubmoduloNav {
  nombre: string;
  href: string;
  icono: React.ComponentType<{ className?: string }>;
}

interface ModuloNav {
  nombre: string;
  href: string;
  icono: React.ComponentType<{ className?: string }>;
  disponible: boolean;
  descripcion: string;
  submodulos?: SubmoduloNav[];
}

const SUBMODULOS_CONFIGURACION_CONTADOR: SubmoduloNav[] = [
  { nombre: "Empresas", href: "/configuracion/empresas", icono: Building2 },
  { nombre: "Usuarios", href: "/configuracion/usuarios", icono: Users },
  { nombre: "DIAN", href: "/configuracion/dian", icono: Link2 },
];

const SUBMODULOS_CONFIGURACION_EMPRESA: SubmoduloNav[] = [
  { nombre: "ERP y PST", href: "/configuracion", icono: Settings },
  { nombre: "DIAN", href: "/configuracion/dian", icono: Link2 },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sesion } = useAuth();

  const modulos: ModuloNav[] = [
    {
      nombre: "Documentos",
      href: "/documentos",
      icono: FileText,
      disponible: true,
      descripcion: "Ingesta, causación y pagos",
    },
    {
      nombre: "Reportes",
      href: "/reportes",
      icono: BarChart3,
      disponible: false,
      descripcion: "KPIs del Agente Reportero",
    },
    {
      nombre: "Conciliación",
      href: "/conciliacion",
      icono: GitCompare,
      disponible: false,
      descripcion: "Cruce bancario",
    },
    {
      nombre: "Seguridad",
      href: "/seguridad",
      icono: ShieldAlert,
      disponible: true,
      descripcion: "Alertas del Agente de Seguridad",
    },
    {
      nombre: "Configuración",
      href: "/configuracion",
      icono: Settings,
      disponible: true,
      descripcion: sesion?.rol === "contador" ? "Empresas, usuarios y DIAN" : "ERP, PST y DIAN",
      submodulos: sesion?.rol === "contador" ? SUBMODULOS_CONFIGURACION_CONTADOR : SUBMODULOS_CONFIGURACION_EMPRESA,
    },
  ];

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-nova-border bg-nova-panel p-4">
      <div className="mb-6 flex items-center gap-2 px-2">
        <Bot className="h-6 w-6 text-nova-accent" />
        <span className="text-lg font-semibold">NOVA</span>
      </div>

      <nav className="flex flex-col gap-1">
        {modulos.map(({ nombre, href, icono: Icono, disponible, descripcion, submodulos }) => {
          const activo = pathname.startsWith(href);
          const expandido = activo && !!submodulos;

          return (
            <div key={nombre}>
              <Link
                href={submodulos ? submodulos[0].href : href}
                className={clsx(
                  "flex items-center gap-3 rounded-lg px-3 py-2 transition-colors",
                  activo ? "bg-nova-accent/15 text-nova-accent" : "text-gray-300 hover:bg-nova-bg"
                )}
              >
                <Icono className="h-4 w-4" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium">{nombre}</p>
                    {!disponible && (
                      <span className="rounded-full bg-nova-bg px-1.5 py-0.5 text-[9px] uppercase text-gray-500">
                        Pronto
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-gray-500">{descripcion}</p>
                </div>
                {submodulos && (
                  <ChevronDown className={clsx("h-3.5 w-3.5 transition-transform", expandido && "rotate-180")} />
                )}
              </Link>

              {submodulos && expandido && (
                <div className="ml-4 mt-1 flex flex-col gap-0.5 border-l border-nova-border pl-3">
                  {(() => {
                    // Coincidencia por prefijo más específico: evita que "/configuracion"
                    // (ERP y PST) se marque activo estando en "/configuracion/dian".
                    const coincidencias = submodulos.filter(
                      (s) => pathname === s.href || pathname.startsWith(`${s.href}/`)
                    );
                    const mejorCoincidencia = coincidencias.sort((a, b) => b.href.length - a.href.length)[0]?.href;
                    return submodulos.map((sub) => {
                      const subActivo = sub.href === mejorCoincidencia;
                      return (
                        <Link
                          key={sub.href}
                          href={sub.href}
                          className={clsx(
                            "flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition-colors",
                            subActivo ? "bg-nova-accent/15 text-nova-accent" : "text-gray-400 hover:bg-nova-bg"
                          )}
                        >
                          <sub.icono className="h-3.5 w-3.5" />
                          {sub.nombre}
                        </Link>
                      );
                    });
                  })()}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
