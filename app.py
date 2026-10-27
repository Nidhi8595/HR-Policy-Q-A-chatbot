import html
import os
import re
import time

import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks_openai import DatabricksOpenAI

VECTOR_SEARCH_INDEX = os.environ["VECTOR_SEARCH_INDEX"]

# Connect to the deployed HR Policy Q&A agent
ENDPOINT_NAME = os.environ.get(
    "SERVING_ENDPOINT", "agents_hr_policy-hr_policy_data-hr_policy_qa_agent"
)

# Only list columns that exist in our handbook_chunks table.
SOURCE_COLUMNS = ["content"]

AVATAR_USER = ":material/person:"
AVATAR_BOT = ":material/support_agent:"

st.set_page_config(
    page_title="Northwind HR Assistant",
    page_icon=":material/forum:",
    layout="centered",
)

# ---------------------------------------------------------------- styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,500;0,600;1,500&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --ink: #0c0e12;
        --panel: #14171d;
        --panel-2: #1a1e26;
        --line: rgba(255, 255, 255, 0.08);
        --text: #ece7dd;
        --muted: #8a8f9c;
        --ember: #e8a24a;
        --ember-soft: rgba(232, 162, 74, 0.14);
        --teal: #5fb3a8;
    }

    /* atmosphere: soft glow + film grain */
    .stApp {
        background:
            radial-gradient(900px 500px at 85% -10%, rgba(232, 162, 74, 0.10), transparent 60%),
            radial-gradient(700px 450px at -5% 20%, rgba(95, 179, 168, 0.07), transparent 60%),
            var(--ink);
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        opacity: 0.05;
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
    }
    header[data-testid="stHeader"] { background: transparent; }

    .block-container {
        max-width: 820px;
        padding-top: 2.5rem;
        padding-bottom: 2rem;
    }

    [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"],
    .stButton button,
    [data-testid="stChatInput"] textarea {
        font-family: 'DM Sans', system-ui, sans-serif;
    }

    /* masthead */
    .eyebrow {
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 0.72rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--ember);
        margin-bottom: 0.9rem;
    }
    .eyebrow::before {
        content: "";
        display: inline-block;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--ember);
        box-shadow: 0 0 12px var(--ember);
        margin-right: 0.6rem;
        vertical-align: middle;
    }
    .masthead h1 {
        font-family: 'Fraunces', Georgia, serif;
        font-weight: 500;
        font-size: 3.2rem;
        line-height: 1.05;
        letter-spacing: -0.02em;
        color: var(--text);
        margin: 0 0 0.8rem 0;
        padding: 0;
    }
    .masthead h1 em {
        font-style: italic;
        color: var(--ember);
    }
    .masthead p {
        color: #b4b0a6;
        font-size: 1.05rem;
        max-width: 560px;
    }
    .pills {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin: 1.2rem 0 1.8rem 0;
    }
    .pill {
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 0.7rem;
        letter-spacing: 0.04em;
        padding: 0.3rem 0.75rem;
        border-radius: 999px;
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.03);
        color: #b9b5ab;
    }
    .rule {
        border: 0;
        border-top: 1px solid var(--line);
        margin-bottom: 1.5rem;
    }

    /* buttons and cards */
    .stButton button {
        text-align: left;
        border: 1px solid var(--line);
        border-radius: 14px;
        background: var(--panel);
        color: var(--text);
        padding: 1rem 1.1rem;
        min-height: 4.2rem;
        transition: border-color 0.18s, transform 0.18s, background 0.18s;
    }
    .stButton button:hover {
        border-color: var(--ember);
        background: var(--panel-2);
        color: var(--text);
        transform: translateY(-2px);
    }
    [data-testid="stSidebar"] .stButton button {
        min-height: auto;
        font-size: 0.88rem;
        padding: 0.7rem 0.85rem;
    }
    [data-testid="stSidebar"] {
        background: #090b0e;
        border-right: 1px solid var(--line);
    }

    /* chat bubbles */
    [data-testid="stChatMessage"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: transparent;
        border: 1px solid transparent;
        border-left: 2px solid var(--ember);
        border-radius: 4px 16px 16px 4px;
    }

    /* chat input */
    [data-testid="stChatInput"] {
        border-radius: 16px;
        border: 1px solid var(--line);
        background: var(--panel);
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: var(--ember);
        box-shadow: 0 0 0 3px var(--ember-soft);
    }

    /* sources */
    .source {
        border: 1px solid var(--line);
        border-left: 3px solid var(--ember);
        background: var(--panel-2);
        padding: 0.8rem 1rem;
        border-radius: 4px 10px 10px 4px;
        font-size: 0.92rem;
        line-height: 1.55;
        margin-bottom: 0.7rem;
        color: #cfcabf;
    }
    .source-head {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 0.68rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 0.5rem;
    }
    .meter {
        flex: 0 0 70px;
        height: 4px;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.08);
        overflow: hidden;
    }
    .meter span {
        display: block;
        height: 100%;
        background: linear-gradient(90deg, var(--teal), var(--ember));
    }

    /* sidebar brand */
    .brand {
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.5rem;
        color: var(--text);
        margin-bottom: 0.1rem;
    }
    .brand em { color: var(--ember); }
    .stat {
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 0.7rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
        padding: 0.6rem 0.8rem;
        border: 1px dashed var(--line);
        border-radius: 10px;
        margin-bottom: 0.8rem;
    }
    .stat b { color: var(--ember); font-weight: 500; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="masthead">
        <div class="eyebrow">Northwind Tech &middot; People Operations</div>
        <h1>Ask the <em>handbook.</em></h1>
        <p>
            Plain answers about leave, expenses, remote work and equipment,
            taken straight from the employee handbook.
        </p>
        <div class="pills">
            <span class="pill">grounded in the handbook</span>
            <span class="pill">sources under every answer</span>
            <span class="pill">admits when it doesn't know</span>
        </div>
        <hr class="rule">
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- state
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(
        '<div class="brand">Northwind <em>HR</em></div>', unsafe_allow_html=True
    )
    st.caption("Your workplace policy companion")

    asked = sum(1 for m in st.session_state.messages if m["role"] == "user")
    st.markdown(
        f'<div class="stat">Questions this session &middot; <b>{asked:02d}</b></div>',
        unsafe_allow_html=True,
    )

    st.markdown("##### Quick questions")

    sample_questions = [
        "How many annual leave days can I carry over?",
        "Do I need a receipt for a $30 expense?",
        "How long is parental leave for a secondary caregiver?",
        "Do we get reimbursement for home internet bills?",
        "What equipment can I request for my home office?",
        "How early must I request remote work?",
    ]

    for i, sample in enumerate(sample_questions):
        if st.button(sample, key=f"sample_{i}", use_container_width=True):
            st.session_state.pending_question = sample

    st.divider()

    transcript = "\n\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state.messages
    )
    st.download_button(
        "Download conversation",
        transcript,
        file_name="hr_conversation.txt",
        disabled=not transcript,
        use_container_width=True,
        icon=":material/download:",
    )

    if st.button(
        "Clear conversation", use_container_width=True, icon=":material/delete:"
    ):
        st.session_state.messages = []
        st.session_state.pop("pending_question", None)
        st.rerun()

    st.caption("Answers are generated by the HR assistant from the employee handbook.")


def get_source_passages(question, keep=3):
    """Fetch the top matching handbook chunks, skipping duplicate text."""
    w = WorkspaceClient()
    results = w.vector_search_indexes.query_index(
        index_name=VECTOR_SEARCH_INDEX,
        columns=SOURCE_COLUMNS,
        query_text=question,
        num_results=keep,
    )

    if not results.result or not results.result.data_array:
        return []

    names = [c.name for c in results.manifest.columns]
    passages, seen = [], set()
    for row in results.result.data_array:
        record = dict(zip(names, row))
        content = record.get("content")
        if not content or content in seen:
            continue
        seen.add(content)
        passages.append(record)
        if len(passages) == keep:
            break
    return passages


def show_sources(sources):
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)} passages)"):
        for i, s in enumerate(sources, start=1):
            head = f"<span>Passage {i:02d}</span>"
            if s.get("document"):
                head += f"<span>{html.escape(str(s['document']))}</span>"
            if s.get("page"):
                head += f"<span>p. {html.escape(str(s['page']))}</span>"
            if s.get("score") is not None:
                try:
                    score = float(s["score"])
                    pct = max(0.0, min(score, 1.0)) * 100
                    head += (
                        f'<span class="meter"><span style="width:{pct:.0f}%"></span></span>'
                        f"<span>{score:.2f}</span>"
                    )
                except (TypeError, ValueError):
                    pass
            st.markdown(
                f'<div class="source"><div class="source-head">{head}</div>'
                f"{html.escape(s['content'])}</div>",
                unsafe_allow_html=True,
            )


def ask_agent(question, history):
    """Send the question and conversation history to the deployed agent."""
    client = DatabricksOpenAI()

    input_messages = [{"role": m["role"], "content": m["content"]} for m in history]
    input_messages.append({"role": "user", "content": question})

    response = client.responses.create(model=ENDPOINT_NAME, input=input_messages)

    if response.output_text:
        return response.output_text

    return "I couldn't find a text response. Please try again."


def typewriter(text):
    """Yield the answer a few characters at a time for a live-typing feel."""
    for chunk in re.findall(r"\S+\s*", text):
        yield chunk
        time.sleep(0.015)


# ---------------------------------------------------------------- input
# Grab the question first so the landing cards hide the moment one is asked
pending_question = st.session_state.pop("pending_question", None)
typed_question = st.chat_input("Ask about leave, expenses, remote work, benefits...")
question = pending_question or typed_question

# ---------------------------------------------------------------- landing
TOPICS = [
    (
        "Leave and benefits",
        "Annual and parental leave",
        "How many annual leave days can I carry over?",
    ),
    (
        "Expenses",
        "Receipts and reimbursement rules",
        "Do I need a receipt for a $30 expense?",
    ),
    (
        "Remote work",
        "Internet costs and approval timing",
        "Do we get reimbursement for home internet bills?",
    ),
    (
        "Home office",
        "Equipment you can request",
        "What equipment can I request for my home office?",
    ),
]

if not st.session_state.messages and not question:
    st.caption("Pick a topic to start, or type your own question below.")
    cols = st.columns(2)
    for i, (title, blurb, q) in enumerate(TOPICS):
        with cols[i % 2]:
            if st.button(
                f"**{i + 1:02d} · {title}**\n\n{blurb}",
                key=f"topic_{i}",
                use_container_width=True,
            ):
                st.session_state.pending_question = q
                st.rerun()

# ---------------------------------------------------------------- history
for idx, message in enumerate(st.session_state.messages):
    avatar = AVATAR_USER if message["role"] == "user" else AVATAR_BOT
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        if message["role"] == "assistant" and not message.get("failed"):
            show_sources(message.get("sources"))
            left, right = st.columns([1, 3])
            with left:
                st.feedback("thumbs", key=f"fb_{idx}")
            with right:
                if message.get("elapsed"):
                    st.caption(f"Answered in {message['elapsed']:.1f}s")

# ---------------------------------------------------------------- new question
if question:
    history = list(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user", avatar=AVATAR_USER):
        st.markdown(question)

    with st.chat_message("assistant", avatar=AVATAR_BOT):
        reply = {"role": "assistant", "content": "", "sources": [], "failed": False}
        with st.status("Searching the handbook...", expanded=False) as status:
            start = time.time()
            try:
                reply["content"] = ask_agent(question, history)
                status.update(label="Checking sources...")
                try:
                    reply["sources"] = get_source_passages(question)
                except Exception as error:
                    reply["sources"] = []
                    st.warning("Could not load source passages.")
                    st.caption(f"{type(error).__name__}: {error}")
                reply["elapsed"] = time.time() - start
                status.update(label="Done", state="complete")
            except Exception as error:
                reply["failed"] = True
                reply["content"] = (
                    "I couldn't reach the HR policy agent. Check that the app has "
                    "permission to query the serving endpoint and that it shows Ready."
                    f"\n\nDetail: `{type(error).__name__}: {error}`"
                )
                status.update(label="Something went wrong", state="error")

        if reply["failed"]:
            st.markdown(reply["content"])
        else:
            st.write_stream(typewriter(reply["content"]))

    st.session_state.messages.append(reply)
    st.rerun()

st.caption(
    "Answers come from the employee handbook. "
    "Check the official policy for important decisions."
)
