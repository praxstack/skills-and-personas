import {defineConfig, type Plugin} from 'vite';
import motionCanvasPlugin from '@motion-canvas/vite-plugin';
import ffmpegPlugin from '@motion-canvas/ffmpeg';
import fs from 'node:fs';
import path from 'node:path';

// Serves <project>/voice/narration.wav at /narration.wav while the editor runs, so the
// editor preview plays the real voice. Never bundled: renders are silent; mix.py adds audio.
function narration(): Plugin {
  const file = path.resolve(__dirname, '../voice/narration.wav');
  return {
    name: 'explainer:narration',
    configureServer(server) {
      server.middlewares.use('/narration.wav', (_req, res) => {
        if (!fs.existsSync(file)) { res.statusCode = 404; res.end(); return; }
        res.setHeader('Content-Type', 'audio/wav');
        fs.createReadStream(file).pipe(res);
      });
    },
  };
}

// both plugins ship as CommonJS: unwrap their default export under ESM
const motionCanvas = ((motionCanvasPlugin as any).default ?? motionCanvasPlugin) as typeof motionCanvasPlugin;
const ffmpeg = ((ffmpegPlugin as any).default ?? ffmpegPlugin) as typeof ffmpegPlugin;

export default defineConfig(({command}) => ({
  base: './',
  plugins: [
    motionCanvas(),
    // the editor's Render button needs the ffmpeg exporter; the headless build does not
    ...(command === 'serve' ? [ffmpeg(), narration()] : []),
    // after motionCanvas(): project.ts uses top-level await (fonts), which needs esnext
    {name: 'explainer:target', config: () => ({build: {target: 'esnext'}})},
  ],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 4000,
    rollupOptions: {input: {render: 'render.html'}},
  },
  server: {port: 9000, host: '127.0.0.1', fs: {allow: ['..']}},
}));
