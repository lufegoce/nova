"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/nav/Sidebar";
import { TopBar } from "@/components/nav/TopBar";
import { SeleccionEmpresa } from "@/components/nav/SeleccionEmpresa";
import { useAuth } from "@/contexts/AuthContext";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { sesion, cargando } = useAuth();

  useEffect(() => {
    if (!cargando && !sesion) router.replace("/login");
  }, [cargando, sesion, router]);

  if (cargando || !sesion) {
    return <div className="flex h-screen items-center justify-center bg-nova-bg text-gray-500">Cargando...</div>;
  }

  if (sesion.rol === "contador" && !sesion.empresa_actual) {
    return <SeleccionEmpresa />;
  }

  return (
    <div className="flex h-screen bg-nova-bg text-gray-100">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar />
        <div className="flex flex-1 flex-col overflow-hidden">{children}</div>
      </div>
    </div>
  );
}
