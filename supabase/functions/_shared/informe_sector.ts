// Genera el informe personalizado "licitaciones abiertas para tu sector y
// zona" que se muestra al final de la entrevista de validación. Reutiliza
// el JSON público que ya sirve la web (misma fuente de datos, sin duplicar
// el pipeline de scraping/export) en vez de tener un segundo generador de
// informes independiente.

const LICITACIONES_JSON_URL = "https://filippo3471.github.io/licitaciones-espana/licitaciones.json";

export interface InformeSector {
  sector: string;
  ccaa: string | null;
  n_licitaciones: number;
  importe_total_eur: number;
  ejemplos: Array<{
    titulo: string;
    organo: string;
    importe: number | null;
    plazo_fecha: string | null;
    detail_url: string | null;
  }>;
  texto: string;
}

let cache: { data: any; fetchedAt: number } | null = null;
const CACHE_TTL_MS = 5 * 60 * 1000;

async function getLicitaciones(): Promise<any[]> {
  if (cache && Date.now() - cache.fetchedAt < CACHE_TTL_MS) return cache.data;
  const resp = await fetch(LICITACIONES_JSON_URL);
  if (!resp.ok) throw new Error(`No se pudo leer licitaciones.json: ${resp.status}`);
  const json = await resp.json();
  cache = { data: json.licitaciones ?? [], fetchedAt: Date.now() };
  return cache.data;
}

export async function generarInformeSector(sector: string, ccaa: string | null): Promise<InformeSector> {
  const todas = await getLicitaciones();
  const ccaaNorm = ccaa?.trim() || null;
  const filtradas = todas.filter((t: any) => {
    if (t.sector !== sector) return false;
    if (ccaaNorm && t.ccaa !== ccaaNorm) return false;
    return true;
  });

  const importeTotal = filtradas.reduce((acc: number, t: any) => acc + (t.importe || 0), 0);
  const ejemplos = filtradas
    .filter((t: any) => t.importe)
    .sort((a: any, b: any) => (b.importe || 0) - (a.importe || 0))
    .slice(0, 5)
    .map((t: any) => ({
      titulo: t.titulo,
      organo: t.organo,
      importe: t.importe,
      plazo_fecha: t.plazo_fecha,
      detail_url: t.detail_url,
    }));

  const money = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0 });
  const zonaTexto = ccaaNorm ? ` en ${ccaaNorm}` : " en toda España";
  let texto = `Ahora mismo hay ${filtradas.length} licitaciones abiertas de "${sector}"${zonaTexto}, por un importe total de ${money.format(importeTotal)}€.`;
  if (ejemplos.length) {
    texto += "\n\nAlgunos ejemplos (las de mayor importe):\n";
    texto += ejemplos
      .map((e) => `- ${e.titulo} — ${e.organo} — ${money.format(e.importe || 0)}€ — plazo: ${e.plazo_fecha || "no especificado"}`)
      .join("\n");
  }

  return { sector, ccaa: ccaaNorm, n_licitaciones: filtradas.length, importe_total_eur: importeTotal, ejemplos, texto };
}
