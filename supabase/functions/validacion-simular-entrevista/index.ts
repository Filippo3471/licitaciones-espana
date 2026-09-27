// Edge Function de USO INTERNO SOLO PARA TESTING (Fase 2, Prompt 4):
// simula una entrevista completa entre el entrevistador real (mismo guion
// que se usará en producción, ver _shared/entrevista.ts) y una persona
// SINTÉTICA generada por LLM, para encontrar fallos del guion antes de
// hablar con ninguna empresa real.
//
// No está enlazada desde ningún frontend público. Protegida por un secreto
// compartido (header x-test-secret) en vez de JWT de usuario, porque no
// hay ningún usuario real detrás de esta llamada.
//
// IMPORTANTE: todo lo que produce esta función es SINTÉTICO. No debe
// usarse jamás como dato de análisis de validación real.

import { GUION_SISTEMA, llamarClaude, type ChatMessage } from "../_shared/entrevista.ts";
import { generarInformeSector } from "../_shared/informe_sector.ts";

const ANTHROPIC_API_KEY = Deno.env.get("ANTHROPIC_API_KEY")!;
const VALIDACION_TEST_SECRET = Deno.env.get("VALIDACION_TEST_SECRET")!;

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-test-secret",
};

interface Turno {
  hablante: "entrevistador" | "persona";
  texto: string;
}

function toMessages(transcript: Turno[], viewpoint: "entrevistador" | "persona"): ChatMessage[] {
  if (transcript.length === 0 && viewpoint === "entrevistador") {
    return [{ role: "user", content: "(Empieza la entrevista formulando tu primera pregunta de contexto. El usuario ya dio su consentimiento.)" }];
  }
  const propio = viewpoint;
  return transcript.map((t) => ({
    role: t.hablante === propio ? "assistant" : "user",
    content: t.texto,
  }));
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });
  try {
    if (req.headers.get("x-test-secret") !== VALIDACION_TEST_SECRET) {
      return jsonResponse({ error: "No autorizado" }, 401);
    }

    const { persona_system_prompt, persona_label, max_turns = 25 } = await req.json();
    if (!persona_system_prompt || !persona_label) {
      return jsonResponse({ error: "Faltan persona_system_prompt / persona_label" }, 400);
    }

    const guionEntrevistador = GUION_SISTEMA();
    const transcript: Turno[] = [];
    let finalizada = false;
    let turnoEntrevistador = 0;
    const TOPE_SEGURIDAD_MENSAJES = 70;

    while (turnoEntrevistador < max_turns && transcript.length < TOPE_SEGURIDAD_MENSAJES) {
      let textoEntrevistador = await llamarClaude(ANTHROPIC_API_KEY, guionEntrevistador, toMessages(transcript, "entrevistador"));
      turnoEntrevistador++;

      const informeMatch = textoEntrevistador.match(/\[MOSTRAR_INFORME sector="([^"]+)" ccaa="([^"]*)"\]/);
      if (informeMatch) {
        try {
          const informe = await generarInformeSector(informeMatch[1], informeMatch[2] || null);
          textoEntrevistador = textoEntrevistador.replace(informeMatch[0], `\n\n${informe.texto}`);
        } catch (e) {
          textoEntrevistador = textoEntrevistador.replace(informeMatch[0], "\n\n[No se pudo generar el informe en esta simulación]");
        }
      }

      const fin = textoEntrevistador.includes("[FIN_ENTREVISTA]");
      textoEntrevistador = textoEntrevistador.replace("[FIN_ENTREVISTA]", "").trim();

      transcript.push({ hablante: "entrevistador", texto: textoEntrevistador });

      if (fin) { finalizada = true; break; }

      const textoPersona = await llamarClaude(ANTHROPIC_API_KEY, persona_system_prompt, toMessages(transcript, "persona"));
      transcript.push({ hablante: "persona", texto: textoPersona });
    }

    return jsonResponse({
      persona_label,
      etiqueta: "SINTÉTICA",
      finalizada_por_guion: finalizada,
      turnos_entrevistador: turnoEntrevistador,
      transcript,
    });
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
