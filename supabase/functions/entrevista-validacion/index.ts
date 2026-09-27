// Edge Function pública (sin JWT, se accede por token no adivinable) que
// conduce la entrevista de validación real (Prompt 4, Fase 3). El mismo
// guion que se probó en Fase 2 (_shared/entrevista.ts), pero aquí cada
// turno lo escribe una persona real, no una simulación.
//
// Reglas duras aplicadas aquí (no delegadas al modelo):
//   - Sin consentimiento registrado, no se genera ni se devuelve ninguna
//     pregunta de entrevista.
//   - Límite de 25 turnos del entrevistador o 20 minutos desde el inicio:
//     al llegar a cualquiera de los dos, se cierra sin llamar más al
//     modelo y se marca como parcial_limite_alcanzado.
//   - Si el token no existe o está de baja, no se hace nada.

import { createClient } from "jsr:@supabase/supabase-js@2";
import { GUION_SISTEMA, llamarClaude, type ChatMessage } from "../_shared/entrevista.ts";
import { generarInformeSector } from "../_shared/informe_sector.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const ANTHROPIC_API_KEY = Deno.env.get("ANTHROPIC_API_KEY")!;

const admin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type",
};

const MAX_TURNOS = 25;
const MAX_MINUTOS = 20;

interface Turno { hablante: "entrevistador" | "persona"; texto: string }

function toMessages(transcript: Turno[], viewpoint: "entrevistador" | "persona"): ChatMessage[] {
  if (transcript.length === 0 && viewpoint === "entrevistador") {
    return [{ role: "user", content: "(Empieza la entrevista formulando tu primera pregunta de contexto. El usuario ya dio su consentimiento.)" }];
  }
  return transcript.map((t) => ({ role: t.hablante === viewpoint ? "assistant" : "user", content: t.texto }));
}

async function procesarTextoEntrevistador(texto: string): Promise<{ texto: string; fin: boolean }> {
  const informeMatch = texto.match(/\[MOSTRAR_INFORME sector="([^"]+)" ccaa="([^"]*)"\]/);
  if (informeMatch) {
    try {
      const informe = await generarInformeSector(informeMatch[1], informeMatch[2] || null);
      texto = texto.replace(informeMatch[0], `\n\n${informe.texto}`);
    } catch {
      texto = texto.replace(informeMatch[0], "\n\n(No se pudo generar el informe ahora mismo, lo recibirás por email.)");
    }
  }
  const fin = texto.includes("[FIN_ENTREVISTA]");
  texto = texto.replace("[FIN_ENTREVISTA]", "").trim();
  return { texto, fin };
}

function limiteAlcanzado(entrevista: any): boolean {
  if (entrevista.turnos_entrevistador >= MAX_TURNOS) return true;
  const minutos = (Date.now() - new Date(entrevista.iniciada_en).getTime()) / 60000;
  return minutos >= MAX_MINUTOS;
}

const MENSAJE_CIERRE_POR_LIMITE =
  "Hemos llegado al tiempo máximo previsto para esta conversación — muchísimas gracias por todo el detalle que me has dado, ha sido muy útil. Si quieres seguir contándonos algo, puedes responder a este email y lo leeremos con calma.";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });
  try {
    const { token, accion, texto } = await req.json();
    if (!token || !accion) return jsonResponse({ error: "Falta token o accion" }, 400);

    const { data: empresa } = await admin
      .from("validacion_empresas")
      .select("*")
      .eq("token", token)
      .maybeSingle();
    if (!empresa) return jsonResponse({ error: "Enlace no válido." }, 404);
    if (empresa.estado_invitacion === "baja") {
      return jsonResponse({ error: "Este contacto se dio de baja y no se puede iniciar la entrevista." }, 403);
    }

    let { data: entrevista } = await admin
      .from("validacion_entrevistas")
      .select("*")
      .eq("empresa_token", token)
      .order("iniciada_en", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (accion === "iniciar") {
      if (!entrevista) {
        const { data: nueva, error } = await admin
          .from("validacion_entrevistas")
          .insert({
            empresa_token: token,
            es_sintetica: false,
            sector: empresa.sector,
            provincia: empresa.provincia,
            tamaño_estimado: empresa.tamaño_estimado,
          })
          .select("*")
          .single();
        if (error) throw error;
        entrevista = nueva;
      }
      return jsonResponse({
        consentimiento_dado: !!entrevista.consentimiento_en,
        transcript: entrevista.transcript,
        estado: entrevista.estado,
      });
    }

    if (accion === "borrar") {
      if (entrevista) {
        await admin.from("validacion_entrevistas").delete().eq("id", entrevista.id);
      }
      return jsonResponse({ borrado: true });
    }

    if (!entrevista) return jsonResponse({ error: "Entrevista no iniciada." }, 400);
    if (entrevista.estado !== "en_curso") {
      return jsonResponse({ error: "Esta entrevista ya ha terminado.", estado: entrevista.estado, transcript: entrevista.transcript });
    }

    if (accion === "consentir") {
      if (entrevista.consentimiento_en) {
        return jsonResponse({ transcript: entrevista.transcript, estado: entrevista.estado });
      }
      const primerTexto = await llamarClaude(ANTHROPIC_API_KEY, GUION_SISTEMA(), toMessages([], "entrevistador"));
      const { texto: textoLimpio, fin } = await procesarTextoEntrevistador(primerTexto);
      const nuevoTranscript: Turno[] = [{ hablante: "entrevistador", texto: textoLimpio }];
      await admin.from("validacion_entrevistas").update({
        consentimiento_en: new Date().toISOString(),
        transcript: nuevoTranscript,
        turnos_entrevistador: 1,
        estado: fin ? "completa" : "en_curso",
        finalizada_en: fin ? new Date().toISOString() : null,
      }).eq("id", entrevista.id);
      return jsonResponse({ transcript: nuevoTranscript, estado: fin ? "completa" : "en_curso" });
    }

    if (accion === "responder") {
      if (!entrevista.consentimiento_en) return jsonResponse({ error: "Falta consentimiento." }, 400);
      if (typeof texto !== "string" || !texto.trim()) return jsonResponse({ error: "Falta texto." }, 400);

      const transcript: Turno[] = [...entrevista.transcript, { hablante: "persona", texto: texto.trim() }];

      if (limiteAlcanzado(entrevista)) {
        transcript.push({ hablante: "entrevistador", texto: MENSAJE_CIERRE_POR_LIMITE });
        await admin.from("validacion_entrevistas").update({
          transcript,
          estado: "parcial_limite_alcanzado",
          finalizada_en: new Date().toISOString(),
        }).eq("id", entrevista.id);
        return jsonResponse({ transcript, estado: "parcial_limite_alcanzado" });
      }

      const textoEntrevistador = await llamarClaude(ANTHROPIC_API_KEY, GUION_SISTEMA(), toMessages(transcript, "entrevistador"));
      const { texto: textoLimpio, fin } = await procesarTextoEntrevistador(textoEntrevistador);
      transcript.push({ hablante: "entrevistador", texto: textoLimpio });

      const nuevosTurnos = entrevista.turnos_entrevistador + 1;
      await admin.from("validacion_entrevistas").update({
        transcript,
        turnos_entrevistador: nuevosTurnos,
        estado: fin ? "completa" : "en_curso",
        finalizada_en: fin ? new Date().toISOString() : null,
      }).eq("id", entrevista.id);

      return jsonResponse({ transcript, estado: fin ? "completa" : "en_curso" });
    }

    return jsonResponse({ error: `Acción desconocida: ${accion}` }, 400);
  } catch (err) {
    return jsonResponse({ error: `Error inesperado: ${(err as Error).message}` }, 500);
  }
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS_HEADERS, "content-type": "application/json" },
  });
}
