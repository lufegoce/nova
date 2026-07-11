"use client";

import { RutEmpresaForm } from "@/components/configuracion/RutEmpresaForm";

export default function ConfiguracionEmpresasPage() {
  return (
    <div className="flex-1 overflow-y-auto p-4">
      <RutEmpresaForm
        onCreada={() => {
          // La nueva empresa queda disponible en el selector de la barra superior.
        }}
      />
    </div>
  );
}
