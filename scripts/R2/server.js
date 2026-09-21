export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        const key = url.pathname.replace(/^\/+/, ""); // enlève le slash initial
        if (!key) {
            return new Response("Missing key", { status: 400 });
        }

        const object = await env.R2_BUCKET.get(key);
        if (!object) {
            return new Response("Not Found", { status: 404 });
        }

        return new Response(object.body, {
            status: 200,
            headers: {
                "Content-Type": object.httpMetadata?.contentType || "application/octet-stream",
                "Cache-Control": "public, max-age=3600",
            },
        });
    },
};