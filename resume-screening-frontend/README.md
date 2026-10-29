# ResumeAI frontend UI update

This package contains the refreshed frontend files only. Existing Flask API routes, extraction flow, model payload, and history behavior have been preserved.

## Replace these files
- `src/App.jsx`
- `src/App.css`
- `src/components/ResumeForm.jsx`

Keep your existing `main.jsx`, `package.json`, assets, and backend as they are.

## Run
From your existing frontend project folder, run `npm run dev`. Ensure Flask is running at `http://127.0.0.1:5000`, or set `VITE_API_BASE_URL` to your backend URL.

Note: the supplied source was pasted with formatting escape characters; these were normalized in the JSX/CSS output. Please keep a backup of your original files before replacing them.
