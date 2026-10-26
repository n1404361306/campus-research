export const dynamic = "force-dynamic";

export function GET() {
  return Response.json(
    { modelConfigured: process.env.CAMPUS_MODEL_CONFIGURED !== "0" },
    { headers: { "Cache-Control": "no-store" } },
  );
}
