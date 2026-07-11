"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { cerrarSesion as cerrarSesionApi, obtenerSesionActual, type SesionActual } from "@/lib/api";

interface AuthContextValor {
  sesion: SesionActual | null;
  cargando: boolean;
  refrescar: () => Promise<void>;
  cerrarSesion: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValor | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [sesion, setSesion] = useState<SesionActual | null>(null);
  const [cargando, setCargando] = useState(true);

  const refrescar = useCallback(async () => {
    setSesion(await obtenerSesionActual());
  }, []);

  useEffect(() => {
    refrescar().finally(() => setCargando(false));
  }, [refrescar]);

  async function cerrarSesion() {
    await cerrarSesionApi();
    setSesion(null);
  }

  return (
    <AuthContext.Provider value={{ sesion, cargando, refrescar, cerrarSesion }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValor {
  const contexto = useContext(AuthContext);
  if (!contexto) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return contexto;
}
