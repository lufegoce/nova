"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ErpConfigForm } from "@/components/configuracion/ErpConfigForm";
import { PstConfigForm } from "@/components/configuracion/PstConfigForm";
import { useAuth } from "@/contexts/AuthContext";

export default function ConfiguracionPage() {
  const { sesion } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (sesion?.rol === "contador") router.replace("/configuracion/empresas");
  }, [sesion, router]);

  if (sesion?.rol === "contador") return null;

  return (
    <div className="flex-1 space-y-4 overflow-y-auto p-4">
      <PstConfigForm />
      <ErpConfigForm />
    </div>
  );
}
