// Edge Function pública (sin JWT): valida un código de invitación contra
// el secreto SIGNUP_INVITE_CODE del proyecto, para dejar el registro
// cerrado por defecto salvo que alguien tenga el link con el código.
//
// Requiere: supabase secrets set SIGNUP_INVITE_CODE=<código>

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const SIGNUP_INVITE_CODE = Deno.env.get("SIGNUP_INVITE_CODE");

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });
  try {
    const { code } = await req.json();
    const valid = !!SIGNUP_INVITE_CODE && typeof code === "string" && code === SIGNUP_INVITE_CODE;
    return new Response(JSON.stringify({ valid }), {
      status: 200,
      headers: { ...CORS_HEADERS, "content-type": "application/json" },
    });
  } catch {
    return new Response(JSON.stringify({ valid: false }), {
      status: 200,
      headers: { ...CORS_HEADERS, "content-type": "application/json" },
    });
  }
});
