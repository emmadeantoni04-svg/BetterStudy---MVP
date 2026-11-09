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
MODELLO = "claude-sonnet-5-5"

CORSI = [
    "Economia Aziendale",
    "Economia e Gestione delle Imprese",
    "Economics, Finance and International Integration (MEFI)",
    "Economia e Legislazione d'Impresa",
    "Altro",
]

st.set_page_config(page_title="StudySprint - UniPv", page_icon="🎓", layout="wide")


def get_secret(nome: str, default=None):
    """Legge un secret da Streamlit o da variabile d'ambiente, senza errori se manca."""
    try:
        return st.secrets[nome]
    except Exception:
        return os.environ.get(nome, default)


# 👉 L'IA reale si attiva da sola se esiste ANTHROPIC_API_KEY nei secrets.
USA_AI_REALE = bool(get_secret("ANTHROPIC_API_KEY"))

# ----------------------------------------------------------------------
# STILE ACCADEMICO
# ----------------------------------------------------------------------
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; color: #800020; text-align: center; font-weight: bold; }
    .sub-title { font-size: 1.05rem; color: #777; text-align: center; margin-bottom: 20px; }
    .stButton > button, .stFormSubmitButton > button {
        background-color: #800020; color: white; border-radius: 6px; font-weight: bold; border: none;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        background-color: #a0002a; color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# TRACCIAMENTO DATI (CSV locale)
# ----------------------------------------------------------------------
def salva_evento(evento: str, valore: str = "") -> None:
    """Salva ogni azione dell'utente: signup, spiegazione, quiz_generato, quiz_completato, feedback."""
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
# FUNZIONI IA
# ----------------------------------------------------------------------
def _chiama_llm(prompt: str) -> str:
    """
    👉 La chiave API viene letta dai secrets (ANTHROPIC_API_KEY), mai scritta nel codice.

    Per usare OpenAI al posto di Anthropic, sostituisci il corpo con:
        from openai import OpenAI
        client = OpenAI(api_key=get_secret("OPENAI_API_KEY"))
        r = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content
    (e imposta USA_AI_REALE = bool(get_secret("OPENAI_API_KEY")))
    """
    import anthropic
    client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))
    r = client.messages.create(
        model=MODELLO,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.content[0].text


SPIEGAZIONE_SIMULATA = r"""
#### 1. Definizione Formale e Quadro Teorico
L'argomento trattato è un pilastro fondamentale nei corsi di Economia. Rappresenta la modalità con cui gli agenti economici (imprese, consumatori, istituzioni) prendono decisioni ottimali in presenza di risorse scarse o vincoli di bilancio.

#### 2. Formulario e Relazioni Analitiche
* **Condizione di ottimalità:** $MR = MC$ *(Ricavo Marginale = Costo Marginale)*
* **Elasticità della domanda:** $E_d = \frac{\% \Delta Q}{\% \Delta P}$
* **Regola d'oro:** quando la domanda è elastica ($|E_d| > 1$), una riduzione del prezzo aumenta il Ricavo Totale ($RT = P \cdot Q$).

#### 3. Spiegazione Pratica e Caso Reale
*Esempio:* se il prezzo del biglietto del trasporto urbano a Pavia aumenta del 10% e gli utenti calano solo del 2%, la domanda è rigida ($|E_d| < 1$): i ricavi totali aumentano, perché gli studenti hanno poche alternative.

#### 4. ⚠️ Trappole Frequenti all'Esame
* Non confondere uno **spostamento lungo la curva** (variazione del prezzo del bene) con uno **spostamento della curva** (reddito, beni sostituti).
* Specifica sempre le ipotesi di partenza (assenza di esternalità, concorrenza perfetta vs monopolio).

#### 5. 💬 Domanda d'Orale Tipica
*"Cosa accade all'equilibrio se lo Stato introduce un'imposta unitaria?"*

**Risposta modello:** la curva di offerta trasla verso l'alto pari all'imposta. Si crea una **perdita secca**: il prezzo pagato dai consumatori sale, quello incassato dai venditori scende.
"""


def genera_spiegazione(testo: str) -> str:
    if not USA_AI_REALE:
        return f"### 📖 Spiegazione (modalità demo): {testo[:60]}\n" + SPIEGAZIONE_SIMULATA
    prompt = (
        "Sei un professore tutor di Economia all'Università di Pavia. "
        "Fornisci una spiegazione approfondita e strutturata in 5 sezioni "
        "(1. Definizione Formale, 2. Formulario/Analisi Matematica, 3. Esempio Pratico Reale, "
        "4. Trappole Frequenti all'Esame, 5. Domanda Tipica d'Orale con risposta modello). "
        "Usa il markdown e le formule con la sintassi $...$. Rispondi in italiano.\n\n"
        f"Testo/argomento dello studente:\n{testo}"
    )
    try:
        return _chiama_llm(prompt)
    except Exception as e:
        return f"⚠️ Errore nella chiamata IA: {e}"


def _quiz_simulato() -> list:
    return [
        {
            "domanda": "Qual è la condizione di ottimalità del profitto per un'impresa in concorrenza perfetta?",
            "opzioni": [
                "A) Prezzo = Costo Fisso Medio",
                "B) Ricavo Marginale = Costo Marginale (MR = MC)",
                "C) Ricavo Totale = Costi Fissi",
                "D) Prezzo = Costo Medio Variabile",
            ],
            "corretta": 1,
            "spiegazione": "In concorrenza perfetta il prezzo è uguale al ricavo marginale ($P = MR$). L'impresa massimizza il profitto dove $MR = MC$.",
        },
        {
            "domanda": "Se la domanda di un bene è rigida (|E| < 1), un aumento del prezzo comporta:",
            "opzioni": [
                "A) Una riduzione del ricavo totale",
                "B) Un aumento del ricavo totale",
                "C) La chiusura immediata dell'impresa",
                "D) Un aumento proporzionale della quantità domandata",
            ],
            "corretta": 1,
            "spiegazione": "Con domanda rigida la quantità cala meno che proporzionalmente rispetto all'aumento del prezzo, quindi il Ricavo Totale sale.",
        },
        {
            "domanda": "La 'Perdita Secca' (Deadweight Loss) in un mercato rappresenta:",
            "opzioni": [
                "A) Il costo di magazzino dei prodotti invenduti",
                "B) La riduzione del surplus totale dovuta a inefficienze o monopolio",
                "C) Le tasse pagate dalle imprese al comune",
                "D) Il valore dei macchinari ammortizzati",
            ],
            "corretta": 1,
            "spiegazione": "La perdita secca misura la perdita di benessere sociale netto quando il mercato non produce la quantità efficiente.",
        },
    ]


def _quiz_valido(quiz) -> bool:
    if not isinstance(quiz, list) or not quiz:
        return False
    for q in quiz:
        if not isinstance(q, dict):
            return False
        opz = q.get("opzioni")
        corr = q.get("corretta")
        if not q.get("domanda") or not isinstance(opz, list) or len(opz) < 2:
            return False
        if len(set(opz)) != len(opz):
            return False
        if not isinstance(corr, int) or not (0 <= corr < len(opz)):
            return False
    return True


def genera_quiz(testo: str) -> list:
    if not USA_AI_REALE:
        return _quiz_simulato()
    prompt = (
        "Crea 3 domande a risposta multipla d'esame universitario di Economia, in italiano, "
        "basate sul testo fornito (4 opzioni, 1 sola corretta). "
        "Rispondi SOLO con JSON valido, senza backtick né testo extra, nel formato:\n"
        '[{"domanda": "...", "opzioni": ["A) ...","B) ...","C) ...","D) ..."], '
        '"corretta": 0, "spiegazione": "..."}]\n'
        '"corretta" è l\'indice (0-3) dell\'opzione giusta.\n\n'
        f"Testo:\n{testo}"
    )
    try:
        raw = _chiama_llm(prompt).strip().replace("```json", "").replace("```", "").strip()
        quiz = json.loads(raw)
        if _quiz_valido(quiz):
            return quiz
    except Exception:
        pass
    st.warning("Il quiz generato dall'IA non era valido: ti mostro un quiz di esempio.")
    return _quiz_simulato()

# ----------------------------------------------------------------------
# STATO DI SESSIONE
# ----------------------------------------------------------------------
defaults = {
    "session_id": str(uuid.uuid4())[:8],
    "tipo": None,            # "spiegazione" | "quiz"
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
with st.sidebar.expander("📊 Area Founder (Esperimento)"):
    pwd = st.text_input("Password Founder", type="password", key="admin_pwd")
    admin_pwd = get_secret("ADMIN_PASSWORD", "founder")
    if pwd == admin_pwd:
        df = carica_eventi()
        n_signup = int((df["evento"] == "signup").sum())
        n_gen = int((df["evento"] == "quiz_generato").sum())
        n_comp = int((df["evento"] == "quiz_completato").sum())
        voti = pd.to_numeric(df.loc[df["evento"] == "feedback", "valore"], errors="coerce").dropna()

        st.metric("Sign-up totali", n_signup)
        st.metric("Quiz Completion Rate",
                  f"{(n_comp / n_gen * 100):.0f}%" if n_gen else "n/d",
                  help=f"{n_comp} completati su {n_gen} generati")
        st.metric("Report Satisfaction (media)",
                  f"{voti.mean():.1f}/10" if len(voti) else "n/d",
                  help=f"{len(voti)} voti")
        st.caption("Modalità IA: " + ("reale ✅" if USA_AI_REALE else "demo (nessuna API key)"))
        st.dataframe(df.tail(30), use_container_width=True)
        st.download_button("📥 Scarica CSV", df.to_csv(index=False),
                           "studysprint_eventi.csv", "text/csv")
    elif pwd:
        st.error("Password errata")

# ----------------------------------------------------------------------
# 1) ONBOARDING (Sign-Up Rate)
# ----------------------------------------------------------------------
if "utente" not in st.session_state:
    st.markdown("<h1 class='main-title'>🎓 StudySprint</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title'>Università di Pavia · Economia<br>"
                "Il tuo assistente AI per studiare: spiegazioni chiare e mock test dai tuoi appunti.</p>",
                unsafe_allow_html=True)

    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        with st.container(border=True):
            st.subheader("Accedi a StudySprint")
            with st.form("signup"):
                nome = st.text_input("Nome")
                corso = st.selectbox("Corso di studi", CORSI)
                ok = st.form_submit_button("Entra in StudySprint", use_container_width=True)
            if ok:
                if not nome.strip():
                    st.error("Inserisci il tuo nome per continuare.")
                else:
                    st.session_state["utente"] = {"nome": nome.strip(), "corso": corso}
                    salva_evento("signup")
                    st.rerun()
    st.stop()

# ----------------------------------------------------------------------
# 2) DASHBOARD PRINCIPALE
# ----------------------------------------------------------------------
utente = st.session_state["utente"]
st.markdown(f"<h2 style='color:#800020;'>Ciao {utente['nome']}! 📚</h2>", unsafe_allow_html=True)
st.caption(f"Corso: {utente['corso']} · Università di Pavia")

testo = st.text_area(
    "Incolla i tuoi appunti o indica l'argomento di studio:",
    height=160,
    placeholder="Es. Elasticità della domanda al prezzo, equilibrio di monopolio, scritture di assestamento...",
)

c1, c2 = st.columns(2)
btn_spiega = c1.button("💡 Spiega questo concetto", use_container_width=True)
btn_quiz = c2.button("📝 Genera Mock Test", use_container_width=True)

if (btn_spiega or btn_quiz) and not testo.strip():
    st.warning("Inserisci prima un argomento o incolla i tuoi appunti nel riquadro sopra.")
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
# 3) OUTPUT IA (Quiz Completion Rate)
# ----------------------------------------------------------------------
st.divider()

if st.session_state.tipo == "spiegazione":
    with st.container(border=True):
        st.markdown(st.session_state.spiegazione)

elif st.session_state.tipo == "quiz":
    st.subheader("📝 Mock Test")
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
        st.success(f"🏆 Punteggio: {punti} / {tot}")
        for i, (q, r) in enumerate(zip(quiz, risposte)):
            giusta = q["opzioni"][q["corretta"]]
            with st.container(border=True):
                if r == giusta:
                    st.markdown(f"✅ **Quesito {i + 1}: corretto**  \n{q['domanda']}  \nLa tua risposta: {r}")
                else:
                    st.markdown(f"❌ **Quesito {i + 1}: errato**  \n{q['domanda']}  \n"
                                f"La tua risposta: _{r}_  \n**Risposta esatta:** {giusta}")
                if q.get("spiegazione"):
                    st.markdown(f"💡 **Spiegazione:** {q['spiegazione']}")

# ----------------------------------------------------------------------
# 4) FEEDBACK (Report Satisfaction, voto 1-10)
# ----------------------------------------------------------------------
pronto_feedback = (
    st.session_state.tipo == "spiegazione"
    or (st.session_state.tipo == "quiz" and st.session_state.quiz_completato)
)
if pronto_feedback:
    st.divider()
    if st.session_state.feedback_dato:
        st.success("Grazie per il tuo feedback! 🙏")
    else:
        with st.form(f"feedback_{st.session_state.output_id}"):
            voto = st.slider("Quanto è stato utile questo strumento per il tuo studio?", 1, 10, 7)
            inv = st.form_submit_button("Invia valutazione")
        if inv:
            salva_evento("feedback", str(voto))
            st.session_state.feedback_dato = True
            st.rerun()
