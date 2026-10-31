\# AI Resume Screening and Candidate Shortlisting System



An intelligent resume screening and candidate shortlisting application built using React, Flask, Python, and Machine Learning.



\## Features



\- Upload resumes in PDF, DOCX, JPG, JPEG, PNG, and WEBP formats.

\- Extract resume text using PyMuPDF, python-docx, and Tesseract OCR.

\- Predict candidate shortlisting using a trained Machine Learning model.

\- Analyze candidate information and skills.

\- View screening history.

\- Delete individual screening records.

\- React-based user interface with Flask REST APIs.



\## Application Screenshots



\### 1. Dashboard

!\[Resume Dashboard](Screenshots/resume\_dashboard.png)



\### 2. Resume Upload

!\[Resume Upload](Screenshots/resume\_upload.png)



\### 3. Resume Screening



!\[Resume Screening - Step 1](Screenshots/resume\_screening%201.png)



!\[Resume Screening - Step 2](Screenshots/resume\_screening%202.png)



\### 4. Screening Results



\*\*Shortlisted Candidate\*\*



!\[Shortlisted Result](Screenshots/resume\_result\_shortlisted.png)



\*\*Not Shortlisted Candidate\*\*



!\[Not Shortlisted Result](Screenshots/resume\_result\_not\_shortlisted.png)



\### 5. Screening History

!\[Screening History](Screenshots/resume\_history.png)



\## Tech Stack



\*\*Frontend:\*\* React, JavaScript, CSS



\*\*Backend:\*\* Python, Flask, Flask-CORS



\*\*Machine Learning:\*\* Scikit-learn, Pandas, NumPy, Joblib



\*\*Resume Processing:\*\* PyMuPDF, python-docx, Pytesseract, Pillow



\*\*Database:\*\* SQLite



\## Project Structure



```text

AI-Resume-Screening-and-Candidate-Shortlisting-System/

│

├── resume-screening-frontend/

│   ├── src/

│   ├── public/

│   └── package.json

│

├── resume\_screening\_backend/

│   ├── app.py

│   ├── requirements.txt

│   └── shortlisting\_model.pkl

│

└── README.md

```



\## Machine Learning Model



The trained model is hosted on Hugging Face because its size exceeds GitHub's standard file upload limit.



\*\*Download Model:\*\*



\[Download shortlisting\_model.pkl](https://huggingface.co/gauranshi05/resume-screening-model/resolve/main/shortlisting\_model.pkl)



Place the downloaded file inside:



`resume\_screening\_backend/`



\## Backend Setup



```bash

cd resume\_screening\_backend



python -m venv .venv



.venv\\Scripts\\activate



pip install -r requirements.txt



python app.py

```



The Flask backend runs locally at:



`http://127.0.0.1:5000`



\## Frontend Setup



Open another terminal:



```bash

cd resume-screening-frontend



npm install



npm run dev

```



\## API Endpoints



| Method | Endpoint | Description |

|---|---|---|

| GET | `/` | Backend status |

| GET | `/model-info` | Model information |

| GET | `/history` | Screening history |

| GET | `/history/<record\_id>` | Individual screening record |

| DELETE | `/history/<record\_id>` | Delete a screening record |

| POST | `/extract-resume` | Extract resume information |

| POST | `/predict` | Predict candidate shortlisting |



\## Notes



\- The trained model file is hosted externally on Hugging Face.

\- The dataset and sensitive files are not included in this repository.

\- Screening history is stored using SQLite.

\- Tesseract OCR must be installed separately for image-based resume extraction.



\## Author



\*\*Gauranshi Varshney\*\*



GitHub: \[Gauranshi07](https://github.com/Gauranshi07)

