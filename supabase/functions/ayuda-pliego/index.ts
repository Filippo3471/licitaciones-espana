// Edge Function: ayuda-pliego
//
// Dado el external_id de una licitación y su lista de documentos (PCAP/PPT),
// devuelve un resumen estructurado del pliego (generado una vez por
// licitación y cacheado en `pliego_summaries`, compartido entre usuarios)
// más una evaluación de encaje calculada al vuelo contra el perfil de la
// empresa que hace la petición (RLS garantiza que solo ve su propio
// perfil). Nunca inventa datos: si el modelo no encuentra un campo en el
// pliego, se devuelve null.
//
// Requiere estos secretos configurados en el proyecto de Supabase:
//   supabase secrets set ANTHROPIC_API_KEY=sk-ant-...
//   supabase secrets set ANTHROPIC_WORKSPACE_ID=wrkspc_...   (solo si la
//     clave no está vinculada a un workspace concreto; la API de Anthropic
//     lo exige en ese caso)
// (SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY los inyecta la plataforma sola)

import { createClient } from "jsr:@supabase/supabase-js@2";

const ANTHROPIC_API_KEY = Deno.env.get("ANTHROPIC_API_KEY");
const ANTHROPIC_WORKSPACE_ID = Deno.env.get("ANTHROPIC_WORKSPACE_ID");
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const RESUMEN_SCHEMA_PROMPT = `Eres un asistente que extrae información objetiva de pliegos de contratación pública española (PCAP/PPT). Analiza el/los documento(s) adjuntos y devuelve ÚNICAMENTE un JSON (sin texto antes ni después, sin markdown) con esta forma exacta:

{
  "objeto": string | null,
  "lotes": [{"numero": string, "descripcion": string, "importe": number | null}] | null,
  "importe_licitacion": number | null,
  "duracion": string | null,
  "solvencia_economica": string[] | null,
  "solvencia_tecnica": string[] | null,
  "clasificacion_exigida": string | null,
  "garantias": string | null,
  "criterios_adjudicacion": [{"criterio": string, "peso": string}] | null,
  "forma_presentacion": string | null,
  "fecha_limite": string | null,
  "riesgos": string[] | null,
  "citas": { "<nombre_de_campo>": string }
}

Reglas estrictas:
- Si un dato no aparece en el documento, ese campo debe ser null (o [] si es una lista vacía). NUNCA inventes ni deduzcas un valor que no esté escrito.
- "citas" debe indicar, para cada campo que sí encontraste, en qué página o sección del documento lo leíste (texto libre breve, p.ej. "página 4, cláusula 8").
- "riesgos" son puntos que un licitador debería vigilar (plazos ajustados, requisitos inusuales, penalizaciones severas...), solo si están explícitos en el texto — no especules.
- Responde solo el JSON.`;

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });

  try {
    if (!ANTHROPIC_API_KEY) {
      return jsonResponse({ error: "ANTHROPIC_API_KEY no configurada en el proyecto" }, 500);
    }

    const authHeader = req.headers.get("Authorization");
    if (!authHeader) return jsonResponse({ error: "Falta autenticación" }, 401);

    const { external_id, documentos, tender } = await req.json();
    if (!external_id || !Array.isArray(documentos)) {
      return jsonResponse({ error: "external_id y documentos son obligatorios" }, 400);
    }

    // Cliente "como el usuario" (respeta RLS) para leer su perfil.
    const userClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      global: { headers: { Authorization: authHeader } },
    });
    const { data: userData, error: userErr } = await userClient.auth.getUser();
    if (userErr || !userData?.user) return jsonResponse({ error: "Sesión inválida" }, 401);

    const { data: profile } = await userClient
      .from("company_profiles")
      .select("*")
      .eq("user_id", userData.user.id)
      .maybeSingle();

    // Cliente con service role (bypassa RLS) para leer/escribir la caché compartida.
    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

    let resumen: Record<string, unknown>;
    const { data: cached } = await adminClient
      .from("pliego_summaries")
      .select("resumen")
      .eq("external_id", external_id)
      .maybeSingle();

    if (cached?.resumen) {
      resumen = cached.resumen as Record<string, unknown>;
    } else {
      const pcap = documentos.find((d: any) => /PCAP/i.test(d.categoria));
      const ppt = documentos.find((d: any) => /PPT/i.test(d.categoria));
      const targets = [pcap, ppt].filter(Boolean);
      if (targets.length === 0) {
        return jsonResponse({ error: "Esta licitación no tiene PCAP/PPT enlazado en la fuente" }, 404);
      }

      const documentBlocks = [];
      for (const doc of targets) {
        const pdfResp = await fetch(doc.url);
        if (!pdfResp.ok) continue;
        const buf = await pdfResp.arrayBuffer();
        const base64 = base64Encode(buf);
        documentBlocks.push({
          type: "document",
          source: { type: "base64", media_type: "application/pdf", data: base64 },
        });
      }
      if (documentBlocks.length === 0) {
        return jsonResponse({ error: "No se pudo descargar ningún PDF de esta licitación" }, 502);
      }

      const anthropicHeaders: Record<string, string> = {
        "content-type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
      };
      if (ANTHROPIC_WORKSPACE_ID) anthropicHeaders["anthropic-workspace-id"] = ANTHROPIC_WORKSPACE_ID;

      const anthropicResp = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: anthropicHeaders,
        body: JSON.stringify({
          model: "claude-sonnet-5",
          max_tokens: 4096,
          temperature: 0.2,
          messages: [
            {
              role: "user",
              content: [...documentBlocks, { type: "text", text: RESUMEN_SCHEMA_PROMPT }],
            },
          ],
        }),
      });

      if (!anthropicResp.ok) {
        const errText = await anthropicResp.text();
        return jsonResponse({ error: `Fallo llamando al LLM: ${errText.slice(0, 300)}` }, 502);
      }
      const anthropicJson = await anthropicResp.json();
      const text = anthropicJson?.content?.[0]?.text ?? "";
      try {
        resumen = JSON.parse(extractJson(text));
      } catch {
        return jsonResponse({ error: "El LLM no devolvió JSON válido" }, 502);
      }

      await adminClient.from("pliego_summaries").upsert({
        external_id,
        fuente: tender?.fuente ?? null,
        resumen,
        model: "claude-sonnet-5",
      });
    }

    const evaluacion = evaluarEncaje(resumen, profile, tender);
    return jsonResponse({ resumen, evaluacion, desde_cache: !!cached });
  } catch (err) {
    return jsonResponse({ error: `Error inesperado: ${(err as Error).message}` }, 500);
  }
});

function evaluarEncaje(resumen: any, profile: any, tender: any) {
  if (!profile) {
    return {
      veredicto: "sin_perfil",
      explicacion: "Completa el perfil de tu empresa para ver una evaluación de encaje.",
      puntos: [],
    };
  }

  const puntos: { tipo: "cumple" | "no_cumple" | "revisar"; texto: string }[] = [];

  // Importe: dentro del rango declarado por la empresa.
  const importe = resumen.importe_licitacion ?? tender?.importe ?? null;
  if (importe != null && (profile.importe_min != null || profile.importe_max != null)) {
    const min = profile.importe_min ?? 0;
    const max = profile.importe_max ?? Infinity;
    if (importe >= min && importe <= max) {
      puntos.push({ tipo: "cumple", texto: `El importe (${importe.toLocaleString("es-ES")} €) está dentro de tu rango habitual.` });
    } else {
      puntos.push({ tipo: "revisar", texto: `El importe (${importe.toLocaleString("es-ES")} €) está fuera del rango que declaraste (${min}–${profile.importe_max ?? "∞"}).` });
    }
  }

  // CPV: solapa con los códigos de interés de la empresa.
  const cpvTender: string[] = tender?.cpv_codes ?? [];
  const cpvEmpresa: string[] = profile.cpv_codes ?? [];
  if (cpvEmpresa.length && cpvTender.length) {
    const overlap = cpvTender.some((c) => cpvEmpresa.some((e) => c.startsWith(e)));
    puntos.push(
      overlap
        ? { tipo: "cumple", texto: "El CPV de la licitación coincide con tus sectores de interés." }
        : { tipo: "revisar", texto: "El CPV de esta licitación no coincide con los sectores que marcaste — revisa si aplica igualmente." }
    );
  }

  // Clasificación empresarial exigida vs. declarada.
  if (resumen.clasificacion_exigida) {
    if (profile.clasificacion_empresarial) {
      puntos.push({
        tipo: "revisar",
        texto: `Se exige clasificación "${resumen.clasificacion_exigida}". Verifica que tu clasificación (${profile.clasificacion_empresarial}) la cubre — esto no se puede comparar automáticamente con fiabilidad.`,
      });
    } else {
      puntos.push({ tipo: "no_cumple", texto: `Se exige clasificación empresarial ("${resumen.clasificacion_exigida}") y no tienes ninguna declarada en tu perfil.` });
    }
  }

  // Facturación mínima habitual: heurística conservadora (no oficial).
  if (importe != null && profile.facturacion_anual != null) {
    if (profile.facturacion_anual >= importe * 0.75) {
      puntos.push({ tipo: "cumple", texto: "Tu facturación anual declarada es holgada frente al importe de este contrato." });
    } else {
      puntos.push({ tipo: "revisar", texto: "Tu facturación anual declarada es baja frente al importe — algunos pliegos piden facturación mínima de 1–1.5x el importe licitado; confírmalo en la solvencia económica exigida." });
    }
  }

  const noCumple = puntos.filter((p) => p.tipo === "no_cumple").length;
  const revisar = puntos.filter((p) => p.tipo === "revisar").length;
  let veredicto: string;
  if (puntos.length === 0) veredicto = "sin_datos_suficientes";
  else if (noCumple > 0) veredicto = "no_apto";
  else if (revisar > 0) veredicto = "apto_con_dudas";
  else veredicto = "apto";

  return {
    veredicto,
    explicacion: "Evaluación orientativa basada en tu perfil declarado y el pliego extraído — no sustituye la revisión del pliego completo.",
    puntos,
  };
}

function extractJson(text: string): string {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start === -1 || end === -1) throw new Error("sin JSON");
  return text.slice(start, end + 1);
}

function base64Encode(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS_HEADERS, "content-type": "application/json" },
  });
}
