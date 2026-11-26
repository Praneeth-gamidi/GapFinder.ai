from pathlib import Path
import pandas as pd
import streamlit as st
import core, llm

st.set_page_config(page_title="GapFinder AI", page_icon="🎯", layout="wide")
if not core.login("demo", "demo123"):
    core.register("demo", "demo123")

# ---------- login ----------
if "user" not in st.session_state:
    st.title("🎯 GapFinder AI")
    st.caption("Find what you don't know. Demo login: demo / demo123")
    name = st.text_input("Username")
    pw = st.text_input("Password (6+ characters)", type="password")
    a, b = st.columns(2)
    if a.button("Log in", type="primary"):
        if core.login(name, pw):
            st.session_state.user = name
            st.rerun()
        st.error("Wrong username or password.")
    if b.button("Create account"):
        if core.register(name, pw):
            st.success("Account created. Now log in.")
        else:
            st.error("Name is taken or empty, or password is too short.")
    st.stop()

user = st.session_state.user
state = core.load_state(user)

with st.sidebar:
    st.write(f"Signed in as **{user}**")
    env = llm.config_from_env()
    provider = st.selectbox("AI provider", ["groq", "gemini"],
                            index=1 if env and env["provider"] == "gemini" else 0)
    key = st.text_input("API key (free)", type="password")
    if key:
        cfg = {"provider": provider, "key": key.strip()}
    else:
        cfg = env
    st.caption("✅ AI mode" if cfg else "⚠️ Offline mode: simple fill-in-the-blank questions only")
    page = st.radio("Go to", ["1 Upload", "2 Topic map", "3 Quiz", "4 Gap report",
                              "5 Revision plan", "6 Explain", "7 Progress"])
    if st.button("Log out"):
        st.session_state.clear()
        st.rerun()

def build(syllabus, notes, papers):
    """notes and papers are lists of (filename, pages)."""
    s = core.empty_state()
    s["topics"] = core.parse_syllabus(syllabus)
    for name, pages in notes:
        s["chunks"] += core.chunk(name, pages)
    for name, pages in papers:
        text = "\n".join(t for _, t in pages)
        s["past"] += [{"text": q, "file": name} for q in core.split_questions(text)]
    if not s["topics"] or not s["chunks"]:
        raise ValueError("Need a syllabus with topics and at least one page of notes.")
    core.map_past(s)
    core.save_state(user, s)
    st.session_state.pop("quiz", None)
    st.session_state.pop("result", None)
    st.success(f"Ready: {len(s['topics'])} topics, {len(s['chunks'])} passages, {len(s['past'])} past questions.")

need_material = page != "1 Upload" and not state["topics"]
if need_material:
    st.info("Upload material first (or load the sample subject).")
    st.stop()

if page == "1 Upload":
    st.header("Upload study material")
    st.warning("Uploading replaces your current subject and quiz history. In AI mode, relevant passages "
               "are sent to the AI provider, so don't upload private information.")
    syl = st.file_uploader("Syllabus (PDF/TXT)", type=["pdf", "txt", "md"])
    notes = st.file_uploader("Textbook chapters and notes", type=["pdf", "txt", "md"], accept_multiple_files=True)
    papers = st.file_uploader("Past papers (numbered questions)", type=["pdf", "txt", "md"], accept_multiple_files=True)
    try:
        if st.button("Process my files", type="primary"):
            if not syl or not notes:
                st.error("Add a syllabus and at least one notes file.")
            else:
                read = lambda f: (f.name, core.read_file(f.name, f.getvalue()))
                text = "\n".join(t for _, t in read(syl)[1])
                build(text, [read(f) for f in notes], [read(f) for f in papers])
        if st.button("Load sample subject (Biology)"):
            get = lambda n: (n, core.read_file(n, (Path(__file__).parent / "sample_data" / n).read_bytes()))
            build(get("syllabus.txt")[1][0][1], [get("notes.txt")], [get("past_paper.txt")])
    except Exception as e:
        st.error(str(e))

elif page == "2 Topic map":
    st.header("Topic map")
    st.dataframe(pd.DataFrame([{"Unit": t["unit"], "Topic": t["name"], "Subtopics": t["sub"],
                                "Past-paper questions": t["exam"],
                                "Source found": "yes" if core.retrieve(t["name"] + " " + t["sub"], state["chunks"], 1) else "NO"}
                               for t in state["topics"]]), hide_index=True, width="stretch")
    st.subheader("Past questions → topics")
    st.dataframe(pd.DataFrame([{"Question": q["text"], "Topic": q["topic"] or "not matched"}
                               for q in state["past"]]), hide_index=True, width="stretch")

elif page == "3 Quiz":
    st.header("Diagnostic quiz")
    rows = core.gap_report(state)
    order = {"Weak": 0, "Untested": 1, "Medium": 2, "Strong": 3}
    names = [r["topic"] for r in sorted(rows, key=lambda r: (order[r["status"]], -r["exam"]))]
    chosen = st.multiselect("Topics (weak and untested first)", names, default=names[:3], max_selections=5)
    per = st.slider("Questions per topic", 2, 5, 3)
    if st.button("Generate quiz", type="primary"):
        quiz = []
        seen = [r["question"] for a in state["attempts"] for r in a["results"]]
        with st.spinner("Retrieving passages and writing questions..."):
            for t in state["topics"]:
                if t["name"] in chosen:
                    try:
                        qs = core.make_questions(cfg, t, state["chunks"], per, seen)
                        if not qs:
                            st.warning(f"No grounded question could be made for '{t['name']}'.")
                        quiz += qs
                    except Exception as e:
                        st.error(f"{t['name']}: {e}")
        st.session_state.quiz = quiz
        st.session_state.qid = st.session_state.get("qid", 0) + 1
        st.session_state.pop("result", None)

    quiz = st.session_state.get("quiz")
    result = st.session_state.get("result")
    if quiz and not result:
        with st.form("quiz_form"):
            answers = []
            for i, q in enumerate(quiz):
                k = f"q{st.session_state.qid}_{i}"
                st.markdown(f"**{i+1}. {q['question']}**")
                st.caption(f"📖 {core.cite(q['source'])}")
                if q["type"] == "mcq":
                    answers.append(st.radio("Answer", q["options"], index=None, key=k, label_visibility="collapsed"))
                else:
                    answers.append(st.text_area("Your answer", key=k))
            done = st.form_submit_button("Submit", type="primary")
        if done:
            try:
                out = []
                with st.spinner("Checking..."):
                    for q, a in zip(quiz, answers):
                        score, feedback = core.grade(cfg, q, a)
                        out.append({"topic": q["topic"], "concept": q.get("concept", q["topic"]),
                                    "question": q["question"], "given": a, "score": score,
                                    "feedback": feedback, "source": q["source"], "quote": q["quote"]})
                state["attempts"].append({"time": core.time.time(), "results": out})
                core.save_state(user, state)
                st.session_state.result = out
                st.rerun()
            except Exception as e:
                st.error(f"Could not grade, nothing was saved. Submit again. ({e})")
    if result:
        st.subheader(f"Score: {sum(r['score'] for r in result):g} / {len(result)}")
        for r in result:
            icon = "✅" if r["score"] == 1 else "🟡" if r["score"] > 0 else "❌"
            st.markdown(f"{icon} **{r['question']}**")
            st.write(r["feedback"])
            with st.expander(f"View source: {core.cite(r['source'])}"):
                st.text(r["quote"])
                st.caption(r["source"]["text"])
        st.info("Open the Gap report to see your diagnosis.")

elif page == "4 Gap report":
    st.header("Gap report")
    rows = core.gap_report(state)
    for status, icon in [("Weak", "🔴"), ("Medium", "🟡"), ("Strong", "🟢"), ("Untested", "⚪")]:
        group = [r for r in rows if r["status"] == status]
        if group:
            st.subheader(f"{icon} {status} ({len(group)})")
            for r in group:
                pct = "" if r["mastery"] is None else f" — {r['mastery']:.0%} (confidence: {r['confidence']})"
                st.markdown(f"**{r['topic']}**{pct}  \n{r['reason']} Past-paper questions: {r['exam']}.")

elif page == "5 Revision plan":
    st.header("Revision plan")
    days = st.number_input("Days available", 1, 60, 5)
    hours = st.number_input("Hours per day", 0.5, 12.0, 2.0, 0.5)
    plan, left = core.make_plan(state, days, hours)
    st.caption("Priority = how weak you are × how often the topic appears in past papers. "
               "It is recalculated after every quiz.")
    st.dataframe(pd.DataFrame(plan), hide_index=True, width="stretch")
    if left:
        st.warning("Not enough time for: " + ", ".join(left))
    st.download_button("Download plan (CSV)", pd.DataFrame(plan).to_csv(index=False), "plan.csv")

elif page == "6 Explain":
    st.header("Explain this topic")
    st.caption("Answers come only from your uploaded material.")
    q = st.text_input("What should I explain?")
    if st.button("Explain", type="primary") and q:
        try:
            answer, passages = core.explain(cfg, q, state["chunks"])
            st.write(answer)
            for i, p in enumerate(passages):
                with st.expander(f"[{i+1}] {core.cite(p)}"):
                    st.write(p["text"])
        except Exception as e:
            st.error(str(e))

elif page == "7 Progress":
    st.header("Progress")
    if not state["attempts"]:
        st.info("Take a quiz first.")
    else:
        data = []
        for i, a in enumerate(state["attempts"], 1):
            df = pd.DataFrame(a["results"])
            for topic, score in df.groupby("topic")["score"].mean().items():
                data.append({"Attempt": i, "Topic": topic, "Score %": round(score * 100)})
        df = pd.DataFrame(data)
        table = df.pivot(index="Attempt", columns="Topic", values="Score %")
        st.line_chart(table)
        st.dataframe(table, width="stretch")
