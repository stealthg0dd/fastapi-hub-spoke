/**
 * Vercel Build Output API v3 builder.
 *
 * Produces:
 *   .vercel/output/
 *     config.json                      ← routes + cleanUrls
 *     static/                          ← served as-is (CDN)
 *       index.html                     ← landing SPA root
 *       assets/                        ← landing JS/CSS/images
 *       portal/
 *         index.html                   ← portal SPA root
 *         assets/                      ← portal assets (base=/portal/)
 *     functions/
 *       api.func/
 *         .vc-config.json              ← python3.12 runtime
 *         handler.py                   ← entry-point exports `app`
 *         requirements.txt
 *         main.py + all hub packages
 *         spokes/                      ← neufin spoke (and others)
 *
 * Vercel invokes this script via `npm run build` (root package.json).
 */

import { execSync }                        from 'child_process';
import { cpSync, mkdirSync, rmSync,
         writeFileSync, readFileSync,
         existsSync }                      from 'fs';
import { join, dirname }                  from 'path';
import { fileURLToPath }                  from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT      = join(__dirname, '..');
const OUT       = join(ROOT, '.vercel', 'output');
const STATIC    = join(OUT,  'static');
const FUNC_DIR  = join(OUT,  'functions', 'api.func');

// ── 1. Clean previous output ──────────────────────────────────────────────────
console.log('[vercel-build] Cleaning .vercel/output …');
rmSync(OUT, { recursive: true, force: true });
mkdirSync(join(STATIC, 'portal'), { recursive: true });
mkdirSync(FUNC_DIR,               { recursive: true });

// ── 2. Build frontends ────────────────────────────────────────────────────────
const env = {
  ...process.env,
  VITE_API_URL:    '/api/v1',
  VITE_PORTAL_URL: '/portal',
  CI: 'false',     // prevent Vite treating warnings as errors
};

console.log('[vercel-build] Building frontend-landing …');
execSync('npm install --legacy-peer-deps && npm run build', {
  cwd:   join(ROOT, 'frontend-landing'),
  stdio: 'inherit',
  env,
});

console.log('[vercel-build] Building frontend-portal …');
execSync('npm install && npm run build', {
  cwd:   join(ROOT, 'frontend-portal'),
  stdio: 'inherit',
  env,
});

// ── 3. Copy static output ─────────────────────────────────────────────────────
console.log('[vercel-build] Copying static files …');
cpSync(join(ROOT, 'frontend-landing', 'dist'), STATIC,                    { recursive: true });
cpSync(join(ROOT, 'frontend-portal',  'dist'), join(STATIC, 'portal'),    { recursive: true });

// ── 4. Copy Python backend into function directory ────────────────────────────
console.log('[vercel-build] Copying backend into api.func …');
// Hub packages (main.py, api/, core/, graph/, middleware/, models/, agents/, mcp/)
cpSync(join(ROOT, 'backend', 'shared_services'), FUNC_DIR, { recursive: true });

// Spokes (neufin and any future spokes)
cpSync(join(ROOT, 'backend', 'spokes'), join(FUNC_DIR, 'spokes'), { recursive: true });

// ── Verify requirements.txt exists before copying ─────────────────────────────
const reqSrc = join(ROOT, 'backend', 'requirements.txt');
const reqDst = join(FUNC_DIR, 'requirements.txt');

if (!existsSync(reqSrc)) {
  throw new Error(`[vercel-build] FATAL: backend/requirements.txt not found at ${reqSrc}`);
}

cpSync(reqSrc, reqDst);

// Log every non-blank, non-comment line so the Vercel build log shows exactly
// which packages will be installed by the Python runtime.
const reqLines = readFileSync(reqSrc, 'utf-8')
  .split('\n')
  .filter(l => l.trim() && !l.trim().startsWith('#'));
console.log(
  `[vercel-build] requirements.txt → ${reqDst}  (${reqLines.length} packages)\n` +
  reqLines.map(l => `    ${l}`).join('\n'),
);

// ── 5. Patch router.py: fix _root for the function directory layout ───────────
//
// Local layout:  backend/shared_services/api/router.py
//   parents[2]  = backend/          ← contains spokes/  ✓
//
// Function layout:  api.func/api/router.py
//   parents[2]  = (Vercel's task root parent — WRONG)
//   parents[1]  = api.func/         ← contains spokes/  ✓
//
console.log('[vercel-build] Patching api/router.py for function layout …');
const routerPath = join(FUNC_DIR, 'api', 'router.py');
writeFileSync(
  routerPath,
  readFileSync(routerPath, 'utf-8').replace(
    "_root = Path(__file__).resolve().parents[2]",
    "_root = Path(__file__).resolve().parents[1]",
  ),
);

// ── 6. Write function entry-point ─────────────────────────────────────────────
writeFileSync(join(FUNC_DIR, 'handler.py'), `\
import sys
import os

# Ensure the function root is importable (main.py, api/, core/, …)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app   # FastAPI ASGI application — Vercel detects this automatically
`);

// ── 7. Write function runtime config ─────────────────────────────────────────
writeFileSync(
  join(FUNC_DIR, '.vc-config.json'),
  JSON.stringify(
    { runtime: 'python3.12', handler: 'handler.py', maxDuration: 30 },
    null, 2,
  ),
);

// ── 8. Write Build Output config.json ────────────────────────────────────────
//
// Route order matters:
//   1. /api/* → Python serverless function
//   2. handle:"filesystem" → serve JS/CSS/image assets verbatim
//   3. /portal/* SPA fallback → portal/index.html
//   4. Landing SPA fallback  → index.html
//
writeFileSync(
  join(OUT, 'config.json'),
  JSON.stringify(
    {
      version:       3,
      cleanUrls:     true,
      trailingSlash: false,

      routes: [
        // ── API ── all /api/... requests go to the Python function
        { src: '/api/(.*)', dest: '/api' },

        // ── Portal SPA ── must come BEFORE filesystem and landing catch-all
        // [^.]+ prevents intercepting .js/.css asset files (they have dots)
        { src: '/portal$',          dest: '/portal/index.html' },
        { src: '/portal/([^.]*)',   dest: '/portal/index.html' },

        // ── Static assets ── serve files verbatim (JS, CSS, images)
        { handle: 'filesystem' },

        // ── Auth / Login ── serve the landing SPA (handles its own routing)
        { src: '/login',    dest: '/index.html' },
        { src: '/signup',   dest: '/index.html' },

        // ── Landing SPA ── everything else serves the landing index
        { src: '/(.*)', dest: '/index.html' },
      ],
    },
    null, 2,
  ),
);

console.log('[vercel-build] Done — .vercel/output/ is ready for Vercel.');
