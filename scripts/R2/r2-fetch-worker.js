/**
 * Cloudflare Worker - R2 Fetch Service
 * 
 * Ce Worker télécharge des fichiers depuis des sources externes (Dropbox, FromSmash, SwissTransfer)
 * et les stocke dans un bucket R2, permettant d'économiser la bande passante du serveur Render.
 * 
 * Architecture:
 * - Render envoie une requête POST légère (~2 Ko) avec l'URL source
 * - Le Worker télécharge le fichier via fetch() (mode pull)
 * - Le fichier est stocké dans R2 avec métadonnées
 * - Le Worker retourne l'URL publique R2
 */

export default {
    async fetch(request, env) {
        // Configuration CORS pour autoriser les requêtes depuis Render
        const corsHeaders = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, User-Agent, X-R2-FETCH-TOKEN',
        };

        // Gestion des requêtes OPTIONS (preflight CORS)
        if (request.method === 'OPTIONS') {
            return new Response(null, {
                status: 204,
                headers: corsHeaders,
            });
        }

        // Vérifier la méthode HTTP
        if (request.method !== 'POST') {
            return new Response(
                JSON.stringify({ success: false, error: 'Method not allowed' }),
                {
                    status: 405,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                }
            );
        }

        const expectedToken = (env && env.R2_FETCH_TOKEN) ? String(env.R2_FETCH_TOKEN) : '';
        if (!expectedToken || expectedToken.trim() === '') {
            return new Response(
                JSON.stringify({ success: false, error: 'Worker not configured (R2_FETCH_TOKEN missing)' }),
                {
                    status: 500,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                }
            );
        }

        const providedToken = request.headers.get('X-R2-FETCH-TOKEN') || '';
        if (providedToken !== expectedToken) {
            return new Response(
                JSON.stringify({ success: false, error: 'Unauthorized' }),
                {
                    status: 401,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                }
            );
        }

        try {
            // Parser le payload JSON
            const payload = await request.json();
            const { source_url, object_key, bucket, provider, email_id } = payload;

            const parseFilenameFromContentDisposition = (value) => {
                if (!value || typeof value !== 'string') {
                    return null;
                }

                const header = value.trim();
                if (!header) {
                    return null;
                }

                const filenameStarMatch = header.match(/filename\*\s*=\s*([^;]+)/i);
                if (filenameStarMatch) {
                    const raw = filenameStarMatch[1].trim();
                    const parts = raw.split("''");
                    const encoded = (parts.length > 1 ? parts.slice(1).join("''") : raw)
                        .replace(/^"|"$/g, '')
                        .trim();
                    try {
                        return decodeURIComponent(encoded);
                    } catch {
                        return encoded;
                    }
                }

                const filenameMatch = header.match(/filename\s*=\s*"?([^";]+)"?/i);
                if (filenameMatch) {
                    return filenameMatch[1].trim();
                }

                return null;
            };

            const sanitizeFilename = (value, contentType) => {
                if (!value || typeof value !== 'string') {
                    value = '';
                }

                let clean = value
                    .replace(/\0/g, '')
                    .replace(/[\r\n]/g, '')
                    .replace(/[\\/]/g, ' ')
                    .trim();

                if (!clean) {
                    clean = 'file';
                }

                clean = clean.replace(/[^\p{L}\p{N} .,_\-()]/gu, '_');
                clean = clean.replace(/\s+/g, ' ').trim();
                if (!clean) {
                    clean = 'file';
                }

                const lower = clean.toLowerCase();
                const hasExt = lower.includes('.') && !lower.endsWith('.');
                if (!hasExt) {
                    const ct = (contentType || '').toLowerCase();
                    if (ct.includes('zip')) {
                        clean += '.zip';
                    } else if (ct.includes('pdf')) {
                        clean += '.pdf';
                    } else if (ct.includes('mp4')) {
                        clean += '.mp4';
                    } else if (ct.includes('jpeg')) {
                        clean += '.jpg';
                    } else if (ct.includes('png')) {
                        clean += '.png';
                    }
                }

                const maxLen = 120;
                if (clean.length > maxLen) {
                    const lastDot = clean.lastIndexOf('.');
                    if (lastDot > 0 && lastDot < clean.length - 1) {
                        const ext = clean.slice(lastDot);
                        const base = clean.slice(0, maxLen - ext.length);
                        clean = base + ext;
                    } else {
                        clean = clean.slice(0, maxLen);
                    }
                }

                return clean;
            };

            // Validation des champs requis
            if (!source_url || !object_key) {
                return new Response(
                    JSON.stringify({
                        success: false,
                        error: 'Missing required fields: source_url and object_key',
                    }),
                    {
                        status: 400,
                        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                    }
                );
            }

            // Validation du domaine source (sécurité)
            const allowedDomains = [
                'dropbox.com',
                'dl.dropboxusercontent.com',
                'fromsmash.com',
                'swisstransfer.com',
                'wetransfer.com',
            ];

            const sourceHost = new URL(source_url).hostname;
            const isAllowed = allowedDomains.some((domain) =>
                sourceHost.includes(domain)
            );

            if (!isAllowed) {
                return new Response(
                    JSON.stringify({
                        success: false,
                        error: `Domain not allowed: ${sourceHost}`,
                    }),
                    {
                        status: 403,
                        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                    }
                );
            }

            const minZipSizeBytes = 1_000_000;
            const isDropboxProvider = provider === 'dropbox';
            const isDropboxFolderShare = (() => {
                try {
                    const urlObj = new URL(source_url);
                    const host = (urlObj.hostname || '').toLowerCase();
                    const path = (urlObj.pathname || '').toLowerCase();
                    return isDropboxProvider && host.includes('dropbox.com') && path.startsWith('/scl/fo/');
                } catch {
                    return false;
                }
            })();

            const rewriteDropboxToDlHost = (urlStr) => {
                try {
                    const urlObj = new URL(urlStr);
                    const host = (urlObj.hostname || '').toLowerCase();
                    const path = (urlObj.pathname || '').toLowerCase();
                    if (!host.endsWith('dropbox.com')) {
                        return urlStr;
                    }
                    if (path.startsWith('/scl/fo/')) {
                        return urlStr;
                    }
                    urlObj.hostname = 'dl.dropboxusercontent.com';
                    return urlObj.toString();
                } catch {
                    return urlStr;
                }
            };

            const fetchTimeoutMs = isDropboxFolderShare ? 120000 : 30000;
            const userAgent =
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
            const doFetch = async (urlStr) =>
                fetch(urlStr, {
                    headers: {
                        'User-Agent': userAgent,
                        Accept: '*/*',
                        'Accept-Encoding': 'identity',
                        'Accept-Language': 'en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7',
                    },
                    signal: AbortSignal.timeout(fetchTimeoutMs),
                    redirect: 'follow',
                });

            // Log de démarrage
            console.log(
                `[R2-FETCH] Starting transfer: provider=${provider}, source=${source_url.substring(0, 60)}...`
            );

            // Télécharger le fichier depuis la source
            const startTime = Date.now();
            let effectiveSourceUrl = source_url;
            let sourceResponse = await doFetch(effectiveSourceUrl);

            if (!sourceResponse.ok) {
                console.error(
                    `[R2-FETCH] Source fetch failed: status=${sourceResponse.status}`
                );
                return new Response(
                    JSON.stringify({
                        success: false,
                        error: `Source fetch failed with status ${sourceResponse.status}`,
                    }),
                    {
                        status: 502,
                        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                    }
                );
            }

            let contentType =
                sourceResponse.headers.get('Content-Type') ||
                'application/octet-stream';

            if (contentType.includes('text/html') && isDropboxProvider && !isDropboxFolderShare) {
                const rewritten = rewriteDropboxToDlHost(effectiveSourceUrl);
                if (rewritten !== effectiveSourceUrl) {
                    effectiveSourceUrl = rewritten;
                    sourceResponse = await doFetch(effectiveSourceUrl);
                    if (sourceResponse.ok) {
                        contentType =
                            sourceResponse.headers.get('Content-Type') ||
                            'application/octet-stream';
                    }
                }
            }

            const upstreamDisposition = sourceResponse.headers.get('Content-Disposition') || '';
            const upstreamFilename = parseFilenameFromContentDisposition(upstreamDisposition);
            const originalFilename = sanitizeFilename(upstreamFilename, contentType);

            if (contentType.includes('text/html')) {
                console.warn(
                    `[R2-FETCH] HTML response detected for ${source_url} (Content-Type=${contentType}). Aborting to avoid storing preview page.`
                );
                return new Response(
                    JSON.stringify({
                        success: false,
                        error: 'Source returned HTML preview instead of file (content-type=text/html)',
                    }),
                    {
                        status: 502,
                        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                    }
                );
            }
            let contentLength = sourceResponse.headers.get('Content-Length');

            if (isDropboxFolderShare && contentLength) {
                const lengthInt = parseInt(contentLength, 10);
                if (!Number.isNaN(lengthInt) && lengthInt > 0 && lengthInt < minZipSizeBytes) {
                    return new Response(
                        JSON.stringify({
                            success: false,
                            error: `Dropbox folder download too small (${lengthInt} bytes)`,
                        }),
                        {
                            status: 502,
                            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                        }
                    );
                }
            }

            // Certains fournisseurs (ex: Dropbox) utilisent un transfert chunked sans Content-Length.
            // Dans ce cas, on lit le flux complet pour connaître la taille exacte.
            let uploadBody = sourceResponse.body;
            if (isDropboxFolderShare) {
                if (!sourceResponse.body) {
                    return new Response(
                        JSON.stringify({
                            success: false,
                            error: 'Missing response body for Dropbox folder download',
                        }),
                        {
                            status: 502,
                            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                        }
                    );
                }

                const lengthInt = contentLength ? parseInt(contentLength, 10) : NaN;
                const hasKnownLength = Number.isFinite(lengthInt) && lengthInt > 0;

                if (!hasKnownLength) {
                    const reader = sourceResponse.body.getReader();
                    const firstRead = await reader.read();
                    if (firstRead.done || !firstRead.value || firstRead.value.length < 2) {
                        return new Response(
                            JSON.stringify({
                                success: false,
                                error: 'Empty response body for Dropbox folder download',
                            }),
                            {
                                status: 502,
                                headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                            }
                        );
                    }

                    const looksLikeZip =
                        firstRead.value[0] === 0x50 && firstRead.value[1] === 0x4b;
                    if (!looksLikeZip) {
                        return new Response(
                            JSON.stringify({
                                success: false,
                                error: 'Dropbox folder download does not look like a ZIP (missing PK header)',
                            }),
                            {
                                status: 502,
                                headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                            }
                        );
                    }

                    const maxBufferedBytes = 50 * 1024 * 1024;
                    const chunks = [firstRead.value];
                    let totalBytes = firstRead.value.byteLength;

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) {
                            break;
                        }
                        if (!value) {
                            continue;
                        }

                        totalBytes += value.byteLength;
                        if (totalBytes > maxBufferedBytes) {
                            throw new Error(
                                'Dropbox folder download has no Content-Length and exceeds buffering limit (50MB)'
                            );
                        }
                        chunks.push(value);
                    }

                    const merged = new Uint8Array(totalBytes);
                    let offset = 0;
                    for (const chunk of chunks) {
                        merged.set(chunk, offset);
                        offset += chunk.byteLength;
                    }

                    uploadBody = merged.buffer;
                    contentLength = String(totalBytes);
                }

                if (!contentLength || contentLength === '0') {
                    contentLength = '';
                }
            } else if (!contentLength || contentLength === '0') {
                const arrayBuffer = await sourceResponse.arrayBuffer();
                uploadBody = arrayBuffer;
                contentLength = String(arrayBuffer.byteLength);
            }

            // Calculer la date d'expiration (24h à partir de maintenant)
            const expirationDate = new Date();
            expirationDate.setHours(expirationDate.getHours() + 24);

            // Uploader vers R2 avec métadonnées d'expiration
            const encodedFilename = encodeURIComponent(originalFilename);
            const cleanQuotedFilename = originalFilename.replace(/"/g, '');

            await env.R2_BUCKET.put(object_key, uploadBody, {
                httpMetadata: {
                    contentType: contentType,
                    contentDisposition: `attachment; filename="${cleanQuotedFilename}"; filename*=UTF-8''${encodedFilename}`,
                },
                customMetadata: {
                    sourceUrl: source_url,
                    effectiveFetchUrl: effectiveSourceUrl,
                    provider: provider || 'unknown',
                    emailId: email_id || 'unknown',
                    originalFilename: originalFilename,
                    uploadedAt: new Date().toISOString(),
                    expiresAt: expirationDate.toISOString(),
                    contentLength: contentLength || 'unknown',
                },
            });

            const elapsedTime = Date.now() - startTime;

            // Construire l'URL publique R2
            const r2_url = `${env.R2_PUBLIC_BASE_URL}/${object_key}`;

            console.log(
                `[R2-FETCH] Transfer completed: object_key=${object_key}, duration=${elapsedTime}ms, size=${contentLength} bytes`
            );

            return new Response(
                JSON.stringify({
                    success: true,
                    r2_url: r2_url,
                    object_key: object_key,
                    original_filename: originalFilename,
                    content_type: contentType,
                    content_length:
                        contentLength && /^\d+$/.test(contentLength) ? parseInt(contentLength, 10) : null,
                    transfer_time_ms: elapsedTime,
                }),
                {
                    status: 200,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                }
            );
        } catch (error) {
            console.error(`[R2-FETCH] Error: ${error.message}`);

            // Détection d'erreurs spécifiques
            let errorMessage = error.message;
            let statusCode = 500;

            if (error.name === 'AbortError' || error.message.includes('timeout')) {
                errorMessage = 'Request timeout (30s exceeded)';
                statusCode = 504;
            } else if (error.message.includes('network')) {
                errorMessage = 'Network error while fetching source';
                statusCode = 502;
            } else if (error.message.includes('exceeds buffering limit')) {
                statusCode = 413;
            }

            return new Response(
                JSON.stringify({
                    success: false,
                    error: errorMessage,
                }),
                {
                    status: statusCode,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                }
            );
        }
    },
};