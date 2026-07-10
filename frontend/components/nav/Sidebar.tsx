"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { Bot, FileText, BarChart3, GitCompare, Settings, ShieldAlert } from "lucide-react";

interface ModuloNav {
  nombre: string;
  href: string;
  icono: React.ComponentType<{ className?: string }>;
  disponible: boolean;
  descripcion: string;
}

const MODULOS: ModuloNav[] = [
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
    descripcion: "Integración con el ERP",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-nova-border bg-nova-panel p-4">
      <div className="mb-6 flex items-center gap-2 px-2">
        <Bot className="h-6 w-6 text-nova-accent" />
        <span className="text-lg font-semibold">NOVA</span>
      </div>

      <nav className="flex flex-col gap-1">
        {MODULOS.map(({ nombre, href, icono: Icono, disponible, descripcion }) => {
          const activo = pathname.startsWith(href);

          return (
            <Link
              key={nombre}
              href={href}
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
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
