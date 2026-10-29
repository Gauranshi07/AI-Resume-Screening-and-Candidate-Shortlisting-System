ResumeAI Premium Product UI Refresh (Option B)

Included files:
- App.jsx
- App.css
- components/ResumeForm.jsx

What changed:
- Premium dark product styling with more restrained accents and improved responsive layouts.
- Analytics panels based on the current /history records: seven-day activity, shortlisted share, count of records with probabilities, and average recorded probability.
- Clickable screening history rows open a candidate detail drawer using only fields returned by the existing history response.
- Prediction result includes a transparent explanation of the returned output and its limitations. No unsupported feature-level explanations are fabricated.
- Resume extraction, existing Flask endpoints (/model-info, /history, /extract-resume, /predict), and the 15-field prediction payload remain unchanged.

Integration:
1. Back up your current frontend src folder.
2. Replace src/App.jsx and src/App.css with the included files.
3. Replace src/components/ResumeForm.jsx with the included component.
4. Keep main.jsx, package.json, and the Flask backend unchanged.
5. Run the frontend as usual.

Notes:
- Analytics are calculated from the history response available in the frontend. The seven-day chart counts records with parseable timestamps.
- The candidate detail drawer can show extra profile fields only if the current /history response contains them. If the API returns only summary fields, the UI explains that limitation instead of inventing details.
- Feature attribution is not claimed unless the prediction API supplies verified per-feature data.
- JSX syntax was checked; browser rendering and live backend integration should be tested in your local environment.


Runtime fix in this package:
- Added the missing selectedCandidate React state used by the candidate detail drawer. Without it, rendering could fail and show a blank screen.
