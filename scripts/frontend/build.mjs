import * as esbuild from "esbuild";

await esbuild.build({
  entryPoints: [
    "frontend/src/video_io.ts",
    "frontend/src/silent_film_emulsion.ts",
  ],
  bundle: true,
  format: "esm",
  platform: "browser",
  target: "es2022",
  sourcemap: true,
  external: [
    "../../../scripts/app.js",
    "../../../scripts/api.js",
    "../../../scripts/widgets.js",
  ],
  outdir: "web/generated",
});
