// cleanup.js
var cleanup_default = {
    async scheduled(event, env, ctx) {
        console.log("[R2-CLEANUP] Starting cleanup job...");
        const startTime = Date.now();
        let deletedCount = 0;
        let scannedCount = 0;
        let errors = 0;
        try {
            const now = /* @__PURE__ */ new Date();
            let cursor = void 0;
            let hasMore = true;
            while (hasMore) {
                const listed = await env.R2_BUCKET.list({
                    limit: 1e3,
                    cursor
                });
                for (const object of listed.objects) {
                    scannedCount++;
                    try {
                        const objectWithMetadata = await env.R2_BUCKET.head(object.key);
                        if (!objectWithMetadata) {
                            continue;
                        }
                        const expiresAtStr = objectWithMetadata.customMetadata?.expiresAt;
                        if (!expiresAtStr) {
                            continue;
                        }
                        const expiresAt = new Date(expiresAtStr);
                        if (now >= expiresAt) {
                            await env.R2_BUCKET.delete(object.key);
                            deletedCount++;
                            console.log(
                                `[R2-CLEANUP] Deleted expired object: ${object.key} (expired at ${expiresAtStr})`
                            );
                        }
                    } catch (error) {
                        errors++;
                        console.error(
                            `[R2-CLEANUP] Error processing object ${object.key}: ${error.message}`
                        );
                    }
                }
                hasMore = listed.truncated;
                cursor = listed.cursor;
            }
            const elapsedTime = Date.now() - startTime;
            console.log(
                `[R2-CLEANUP] Cleanup completed: scanned=${scannedCount}, deleted=${deletedCount}, errors=${errors}, duration=${elapsedTime}ms`
            );
        } catch (error) {
            console.error(`[R2-CLEANUP] Fatal error: ${error.message}`);
        }
    }
};
export {
    cleanup_default as default
};
//# sourceMappingURL=cleanup.js.map