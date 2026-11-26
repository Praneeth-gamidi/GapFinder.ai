# GapFinder AI (prototype)

## Run
1. Install Python 3.10 or newer (Windows: tick "Add Python to PATH").
2. In this folder:
       pip install -r requirements.txt
       python -m streamlit run app.py
3. Open http://localhost:8501 and log in with `demo` / `demo123`.
4. Upload page -> "Load sample subject".

## Free AI key (no card needed for the free plan)
- Groq: https://console.groq.com/keys  (default)
- Gemini: https://aistudio.google.com/apikey
Paste the key in the sidebar, or set GROQ_API_KEY / GEMINI_API_KEY before starting.
Never commit a key to GitHub. If a model name is retired, edit PROVIDERS in llm.py
(or set LLM_MODEL when using an environment key).

Without a key the app runs in offline mode (fill-in-the-blank questions only).

## Where retrieval and generation happen
| Step | Retrieval (core.py, BM25, local) | Generation (llm.py) | Plain code |
|---|---|---|---|
| Topic map | | | syllabus parsing |
| Past-question mapping | yes | | |
| Quiz | finds 4 passages | writes questions from them | rejects unverifiable quotes |
| Grading | uses the cited passage | grades short answers | grades MCQs |
| Gap report and plan | | | scoring and priority |
| Explain | finds passages | explains with citations | |

The quote check proves the quote exists in the source. It does not prove the question
or answer is correct, so spot-check questions before a demo.

## Limits
- Retrieval is keyword-based, so synonyms can be missed.
- Scanned PDFs are not read.
- Syllabus format: "Unit ..." lines, then one topic per line (optional ": subtopics").
- One subject per user. No teacher view yet.
- demo/demo123 is for judging only.
