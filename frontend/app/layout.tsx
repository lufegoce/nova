import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NOVA · Command Center",
  description: "Plataforma de agentes autónomos para automatización financiera y contable",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
