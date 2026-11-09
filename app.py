# app.py — StudySprint MVP (Università di Pavia, Economia)
import csv
import json
import os
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------
# CONFIGURAZIONE
# ----------------------------------------------------------------------
CSV_PATH = "studysprint_eventi.csv"
CAMPI = ["timestamp", "session_id", "evento", "nome", "corso", "valore"]

# 👉 Metti True per usare l'IA reale (Anthropic). Con False l'app usa risposte simulate.
USA_AI_REALE = False
MODELLO = "claude-sonnet-5-5"

CORSI = [
    "Economia e Management",
    "Economia, Finanza e Mercati",
    "Economia e Commercio",
    "Magistrale (Economia)",
    "Altro",
]

st.set_page_config(page_title="StudySprint - Pavia", page_icon="🎓", layout="centered")

# ----------------------------------------------------------------------
# TRACCIAMENTO DATI (CSV locale)
# ----------------------------------------------------------------------
def salva_evento(evento: str, valore: str = "") -> None:
    """Salva un evento: signup, spiegazione, quiz_generato, quiz_completato, feedback."""
    nuovo_file = not os.path.exists(CSV_PATH)
    utente = st.session_state.get("utente", {})
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPI)
        if nuovo_file:
            w.writeheader()
        w.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "session_id": st.session_state.get("session_id", ""),
            "evento": evento,
            "nome": utente.get("nome", ""),
            "corso": utente.get("corso", ""),
            "valore": valore,
        })


def carica_eventi() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame(columns=CAMPI)
    return pd.read_csv(CSV_PATH)

# ----------------------------------------------------------------------
# FUNZIONI IA  (qui inserisci la tua API key)
# ----------------------------------------------------------------------
def _chiama_llm(prompt: str) -> str:
    """
    👉 QUI VA LA TUA API KEY.
    Per Anthropic: aggiungi ANTHROPIC_API_KEY ai secrets di Streamlit
    (o in .streamlit/secrets.toml in locale). NON scriverla mai nel codice.

    Per usare OpenAI, sostituisci il corpo con:
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        r = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content
    """
    import anthropic
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    r = client.messages.create(
        model=MODELLO,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.content[0].text


def genera_spiegazione(testo: str) -> str:
    if not USA_AI_REALE:
        return (
            "**Spiegazione generata dall'IA (simulata)**\n\n"
            f"Hai chiesto di spiegare: _{testo[:200]}_\n\n"
            "1. **Idea chiave**: il concetto in due righe, in parole semplici.\n"
            "2. **Esempio pratico**: un caso concreto di economia reale.\n"
            "3. **Errore comune**: cosa si confonde spesso all'esame."
        )
    prompt = (
        "Sei un tutor universitario di Economia. Spiega in italiano, in modo semplice "
        "e strutturato (idea chiave, esempio pratico, errore comune all'esame) il "
        f"seguente argomento/appunto:\n\n{testo}"
    )
    try:
        return _chiama_llm(prompt)
    except Exception as e:
        return f"⚠️ Errore nella chiamata IA: {e}"


def _quiz_simulato(testo: str) -> list:
    return [
        {
            "domanda": "Quale tra queste è la definizione più corretta di costo opportunità?",
            "opzioni": [
                "Il costo monetario sostenuto per un bene",
                "Il valore della migliore alternativa a cui si rinuncia",
                "Il costo fisso di produzione",
                "La differenza tra ricavi e costi",
            ],
            "corretta": 1,
        },
        {
            "domanda": "In un mercato concorrenziale, un aumento della domanda a offerta invariata provoca:",
            "opzioni": [
                "Riduzione del prezzo di equilibrio",
                "Nessuna variazione del prezzo",
                "Aumento del prezzo e della quantità di equilibrio",
                "Riduzione della quantità di equilibrio",
            ],
            "corretta": 2,
        },
        {
            "domanda": "Un aumento generalizzato e persistente dei prezzi si chiama:",
            "opzioni": ["Deflazione", "Inflazione", "Recessione", "Stagnazione"],
            "corretta": 1,
        },
    ]


def genera_quiz(testo: str) -> list:
    """Ritorna una lista di dict: {domanda, opzioni[4], corretta (indice 0-3)}."""
    if not USA_AI_REALE:
        return _quiz_simulato(testo)
    prompt = (
        "Sei un tutor universitario di Economia. Crea 3 domande a risposta multipla "
        "(4 opzioni, una sola corretta) in italiano basate su questi appunti.\n"
        "Rispondi SOLO con JSON valido, senza testo extra né backtick, nel formato:\n"
        '[{"domanda": "...", "opzioni": ["a","b","c","d"], "corretta": 0}]\n\n'
        f"Appunti:\n{testo}"
    )
    try:
        raw = _chiama_llm(prompt).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        quiz = json.loads(raw)
        assert isinstance(quiz, list) and len(quiz) > 0
        return quiz
    except Exception:
        st.warning("Quiz IA non valido: uso un quiz di esempio.")
        return _quiz_simulato(testo)

# ----------------------------------------------------------------------
# STATO DI SESSIONE
# ----------------------------------------------------------------------
defaults = {
    "session_id": str(uuid.uuid4())[:8],
    "tipo": None,              # "spiegazione" | "quiz"
    "spiegazione": "",
    "quiz": [],
    "quiz_completato": False,
    "punteggio": None,
    "output_id": "",
    "feedback_dato": False,
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ----------------------------------------------------------------------
# SIDEBAR FOUNDER (metriche dell'esperimento)
# ----------------------------------------------------------------------
with st.sidebar.expander("📊 Area Founder"):
    pwd = st.text_input("Password", type="password", key="admin_pwd")
    admin_pwd = st.secrets.get("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD", "founder"))
    if pwd == admin_pwd:
        df = carica_eventi()
        n_signup = (df["evento"] == "signup").sum()
        n_gen = (df["evento"] == "quiz_generato").sum()
        n_comp = (df["evento"] == "quiz_completato").sum()
        voti = pd.to_numeric(df.loc[df["evento"] == "feedback", "valore"], errors="coerce")
        st.metric("Sign-up", int(n_signup))
        st.metric("Quiz Completion Rate", f"{(n_comp / n_gen * 100):.0f}%" if n_gen else "n/d",
                  help=f"{n_comp} completati su {n_gen} generati")
        st.metric("Report Satisfaction (media)", f"{voti.mean():.1f}/10" if len(voti) else "n/d",
                  help=f"{len(voti)} voti")
        st.dataframe(df.tail(50), use_container_width=True)
        st.download_button("Scarica CSV", df.to_csv(index=False), "studysprint_eventi.csv", "text/csv")
    elif pwd:
        st.error("Password errata")

# ----------------------------------------------------------------------
# 1) ONBOARDING
# ----------------------------------------------------------------------
if "utente" not in st.session_state:
    st.title("🎓 StudySprint")
    st.subheader("Università di Pavia · Economia")
    st.write("Il tuo assistente AI per studiare meglio e più in fretta: spiegazioni "
             "chiare e mock test generati dai tuoi appunti.")
    st.divider()
    with st.form("signup"):
        nome = st.text_input("Nome")
        corso = st.selectbox("Corso di studi", CORSI)
        ok = st.form_submit_button("Entra in StudySprint")
    if ok:
        if not nome.strip():
            st.error("Inserisci il tuo nome per continuare.")
        else:
            st.session_state["utente"] = {"nome": nome.strip(), "corso": corso}
            salva_evento("signup")
            st.rerun()
    st.stop()

# ----------------------------------------------------------------------
# 2) DASHBOARD
# ----------------------------------------------------------------------
utente = st.session_state["utente"]
st.title("🎓 StudySprint")
st.caption(f"Ciao {utente['nome']} · {utente['corso']} · Università di Pavia")

testo = st.text_area(
    "Incolla i tuoi appunti o indica l'argomento di studio",
    height=200,
    placeholder="Es. Elasticità della domanda al prezzo...",
)

c1, c2 = st.columns(2)
btn_spiega = c1.button("💡 Spiega questo concetto", use_container_width=True)
btn_quiz = c2.button("📝 Genera Mock Test", use_container_width=True)

if (btn_spiega or btn_quiz) and not testo.strip():
    st.warning("Scrivi prima un argomento o incolla degli appunti.")
elif btn_spiega:
    with st.spinner("Sto preparando la spiegazione..."):
        st.session_state.spiegazione = genera_spiegazione(testo)
    st.session_state.update(tipo="spiegazione", output_id=str(uuid.uuid4()), feedback_dato=False)
    salva_evento("spiegazione")
elif btn_quiz:
    with st.spinner("Sto generando il mock test..."):
        st.session_state.quiz = genera_quiz(testo)
    st.session_state.update(tipo="quiz", quiz_completato=False, punteggio=None,
                            output_id=str(uuid.uuid4()), feedback_dato=False)
    salva_evento("quiz_generato")

# ----------------------------------------------------------------------
# 3) OUTPUT IA
# ----------------------------------------------------------------------
st.divider()
if st.session_state.tipo == "spiegazione":
    st.subheader("Spiegazione")
    st.markdown(st.session_state.spiegazione)

elif st.session_state.tipo == "quiz":
    st.subheader("Mock Test")
    quiz = st.session_state.quiz
    oid = st.session_state.output_id

    if not st.session_state.quiz_completato:
        with st.form(f"quiz_{oid}"):
            risposte = []
            for i, q in enumerate(quiz):
                r = st.radio(f"**{i + 1}. {q['domanda']}**", q["opzioni"],
                             index=None, key=f"q_{oid}_{i}")
                risposte.append(r)
            invia = st.form_submit_button("Invia risposte")
        if invia:
            if any(r is None for r in risposte):
                st.warning("Rispondi a tutte le domande prima di inviare.")
            else:
                punti = sum(q["opzioni"].index(r) == q["corretta"] for q, r in zip(quiz, risposte))
                st.session_state.punteggio = (punti, len(quiz), risposte)
                st.session_state.quiz_completato = True
                salva_evento("quiz_completato", f"{punti}/{len(quiz)}")
                st.rerun()
    else:
        punti, tot, risposte = st.session_state.punteggio
        st.success(f"Punteggio: {punti}/{tot}")
        for i, (q, r) in enumerate(zip(quiz, risposte)):
            giusta = q["opzioni"][q["corretta"]]
            if r == giusta:
                st.markdown(f"✅ **{i + 1}.** {q['domanda']} → {r}")
            else:
                st.markdown(f"❌ **{i + 1}.** {q['domanda']} → hai risposto _{r}_, corretta: **{giusta}**")

# ----------------------------------------------------------------------
# 4) FEEDBACK (voto 1-10)
# ----------------------------------------------------------------------
pronto_feedback = (
    st.session_state.tipo == "spiegazione"
    or (st.session_state.tipo == "quiz" and st.session_state.quiz_completato)
)
if pronto_feedback:
    st.divider()
    if st.session_state.feedback_dato:
        st.info("Grazie per il tuo feedback! 🙏")
    else:
        with st.form(f"feedback_{st.session_state.output_id}"):
            voto = st.slider("Quanto è stato utile questo strumento per il tuo studio?", 1, 10, 7)
            inv = st.form_submit_button("Invia valutazione")
        if inv:
            salva_evento("feedback", str(voto))
            st.session_state.feedback_dato = True
            st.rerun()
