import { Construction } from "lucide-react";

interface Props {
  titulo: string;
  descripcion: string;
}

export function ModuloPlaceholder({ titulo, descripcion }: Props) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
      <Construction className="h-10 w-10 text-gray-600" />
      <h1 className="text-xl font-semibold text-gray-300">{titulo}</h1>
      <p className="max-w-sm text-sm text-gray-500">{descripcion}</p>
    </div>
  );
}
