"use client";

import { UsuariosEmpresaPanel } from "@/components/configuracion/UsuariosEmpresaPanel";
import { useAuth } from "@/contexts/AuthContext";

export default function ConfiguracionUsuariosPage() {
  const { sesion } = useAuth();

  if (!sesion?.empresa_actual) {
    return (
      <div className="flex-1 p-4 text-sm text-gray-400">
        Selecciona una empresa en la barra superior para gestionar sus usuarios.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <UsuariosEmpresaPanel empresaId={sesion.empresa_actual.id} />
    </div>
  );
}
