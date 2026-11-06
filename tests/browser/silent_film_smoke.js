/** Check Silent Film registration and runtime extensions without queuing work. */
async (sharedPage) => {
    const context = await sharedPage.context().browser().newContext();
    const page = await context.newPage();
    const baseURL = "http://127.0.0.1:8188";
    const extensionPath = "/extensions/ComfyUI_ALEXZ_SilentFilm/";
    const report = { status: "FAIL", checks: [], failures: [], blockedRequests: [] };
    const requiredNodes = [
        "VideoSilentFilmCadence", "VideoSilentFilmFinish", "VideoFrameSelect", "VideoPreviewFrame",
        "VideoLoadSource", "VideoSaveFinal", "VideoSilentFilmCamera", "VideoSilentFilmNegative",
        "VideoSilentFilmPrint", "VideoSilentFilmProjector", "VideoSilentFilmCaptureDirt",
        "VideoSilentFilmNegativeDevelopment", "VideoSilentFilmNegativeDamage", "VideoSilentFilmPrintingDirt",
        "VideoSilentFilmPositiveDevelopment", "VideoSilentFilmPositiveDamage", "VideoSilentFilmProjectorDirt",
    ];
    const requiredExtensions = [
        "ALEXZ.Tools.VideoFrameSelect", "ALEXZ.Tools.VideoIO", "ALEXZ.Tools.SilentFilmEmulsion",
        "ALEXZ.Tools.SilentFilmPreview", "ALEXZ.SilentFilm.WidgetVisibilityProfiles",
    ];
    try {
        page.on("pageerror", (error) => report.failures.push(error.stack || error.message));
        page.on("console", (message) => {
            if (message.type() === "error" && message.location().url.includes(extensionPath)) {
                report.failures.push(`${message.text()} ${message.location().url}`);
            }
        });
        page.on("requestfailed", (request) => {
            if (new URL(request.url()).pathname.startsWith(extensionPath)) {
                report.failures.push(`Request failed: ${request.url()} ${request.failure()?.errorText}`);
            }
        });
        page.on("response", (resource) => {
            if (new URL(resource.url()).pathname.startsWith(extensionPath) && resource.status() >= 400) {
                report.failures.push(`HTTP ${resource.status()}: ${resource.url()}`);
            }
        });
        await page.route(/\/(?:prompt|queue|install|update)(?:\?|$)|\/alexz\/video\/upload(?:\?|$)/, async (route) => {
            report.blockedRequests.push(`${route.request().method()} ${route.request().url()}`);
            await route.abort("blockedbyclient");
        });

        const response = await page.goto(baseURL, { waitUntil: "load", timeout: 60000 });
        if (!response?.ok()) throw new Error("ComfyUI document did not return HTTP 2xx");
        await page.waitForFunction(() => {
            const app = window.comfyAPI?.app?.app;
            return document.readyState === "complete" && app?.vueAppReady && app?.graph && app?.canvas;
        }, null, { timeout: 60000 });
        report.checks.push({ name: "ComfyUI loaded", status: "PASS" });

        await page.waitForFunction((names) => {
            const registered = new Set(window.comfyAPI?.app?.app?.extensions?.map((extension) => extension.name) ?? []);
            return names.every((name) => registered.has(name));
        }, requiredExtensions, { timeout: 60000 });
        report.checks.push({ name: "Silent Film frontend extensions registered", status: "PASS" });

        const definitions = await page.evaluate(async () => {
            const response = await fetch("/object_info");
            if (!response.ok) throw new Error(`GET /object_info: HTTP ${response.status}`);
            return response.json();
        });
        const missing = requiredNodes.filter((name) => !Object.hasOwn(definitions, name));
        if (missing.length) throw new Error(`Missing node definitions: ${missing.join(", ")}`);
        report.checks.push({ name: "All 17 Silent Film node definitions available", status: "PASS" });

        if (report.failures.length) throw new Error(report.failures.join("\n"));
        report.status = "PASS";
        console.log(JSON.stringify(report, null, 2));
        return report;
    } catch (error) {
        report.failures.push(String(error));
        console.log(JSON.stringify(report, null, 2));
        throw error;
    } finally {
        await context.close();
    }
}
