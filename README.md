# QE Post-processing Lab

GUI scaffold for the self-service DFT post-processing tool described in
`Post-Processing-WebApp-Outline.md` (in the sibling `CrystalEdu-App` folder). This is the
interface only: uploads, parameter forms, and zip downloads all work end to end, but every
module's actual processing script is a placeholder for now.

## Scope

- Post-processing and input-generation only. No page runs a real Quantum ESPRESSO calculation.
- Every module page is generated from a single template (`components/TaskPage.jsx`) driven by
  `lib/modules.js`, which mirrors the outline's tables. To add a real script for a module: replace
  the placeholder logic in `app/api/process/route.js` for that `moduleId`, then update its `status`
  in `lib/modules.js`.
- Unlike CrystalEdu Lab, this app is not a static export — file upload and zip generation need a
  real server endpoint (`app/api/process/route.js`), so it deploys to Vercel as a normal Next.js
  app, not a static site.

## Run locally

```bash
npm install
npm run dev
```

Then open http://localhost:3000.
