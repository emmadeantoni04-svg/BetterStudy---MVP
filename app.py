# app.py — StudySprint MVP (Università di Pavia, Economia)
import csv
import json
import os
import random
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------
# CONFIGURAZIONE
# ----------------------------------------------------------------------
CSV_PATH = "studysprint_eventi_v2.csv"
CAMPI = ["timestamp", "session_id", "evento", "nome", "corso", "valore", "dettaglio", "commento"]
MODELLO = "claude-sonnet-5-5"
OPZIONI_N_DOMANDE = [3, 5, 8, 10]

CORSI = [
    "Economia Aziendale",
    "Economia e Gestione delle Imprese",
    "Economia e Legislazione d'Impresa",
    "MIBE - International Business and Economics (in inglese)",
    "Finance (in inglese)",
    "Economics, Finance and International Integration - MEFI (in inglese)",
    "Altro",
]
# Corsi in inglese: per questi la lingua dell'IA parte su English.
CORSI_INGLESE = {
    "MIBE - International Business and Economics (in inglese)",
    "Finance (in inglese)",
    "Economics, Finance and International Integration - MEFI (in inglese)",
}
LINGUE = ["Italiano", "English"]

st.set_page_config(page_title="StudySprint - UniPv", page_icon="🎓", layout="wide")


def get_secret(nome: str, default=None):
    """Legge un secret da Streamlit o da variabile d'ambiente, senza errori se manca."""
    try:
        return st.secrets[nome]
    except Exception:
        return os.environ.get(nome, default)


# L'IA reale si attiva da sola se esiste ANTHROPIC_API_KEY nei secrets.
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
def salva_evento(evento: str, valore: str = "", dettaglio: str = "", commento: str = "") -> None:
    """Eventi: signup, spiegazione, quiz_generato, quiz_completato, feedback."""
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
            "dettaglio": dettaglio,
            "commento": commento,
        })


def carica_eventi() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame(columns=CAMPI)
    return pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)


def etichetta_gradimento(voto) -> str:
    if voto is None or pd.isna(voto):
        return "— nessun voto"
    if voto >= 7:
        return "👍 Gli piace"
    if voto >= 5:
        return "😐 Neutro"
    return "👎 Non gli piace"


def riepilogo_utenti(df: pd.DataFrame) -> pd.DataFrame:
    """Una riga per ogni sessione/utente: cosa ha fatto e se gli è piaciuto."""
    if df.empty:
        return pd.DataFrame()
    righe = []
    for _, g in df.groupby("session_id", sort=False):
        voti = pd.to_numeric(g.loc[g["evento"] == "feedback", "valore"], errors="coerce").dropna()
        completati = g[g["evento"] == "quiz_completato"]
        media = voti.mean() if len(voti) else None
        righe.append({
            "Nome": g["nome"].iloc[0],
            "Corso": g["corso"].iloc[0],
            "Spiegazioni": int((g["evento"] == "spiegazione").sum()),
            "Quiz generati": int((g["evento"] == "quiz_generato").sum()),
            "Quiz completati": len(completati),
            "Ultimo punteggio": completati["valore"].iloc[-1] if len(completati) else "—",
            "Voto medio": round(media, 1) if media is not None else None,
            "Gradimento": etichetta_gradimento(media),
            "Ultima attività": g["timestamp"].iloc[-1],
        })
    return pd.DataFrame(righe).sort_values("Ultima attività", ascending=False)

# ----------------------------------------------------------------------
# FUNZIONI IA
# ----------------------------------------------------------------------
def _chiama_llm(prompt: str, max_tokens: int = 2000) -> str:
    """
    👉 La chiave API viene letta dai secrets (ANTHROPIC_API_KEY), mai scritta nel codice.

    Per usare OpenAI al posto di Anthropic, sostituisci il corpo con:
        from openai import OpenAI
        client = OpenAI(api_key=get_secret("OPENAI_API_KEY"))
        r = client.chat.completions.create(
            model="gpt-4o-mini", max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content
    (e imposta USA_AI_REALE = bool(get_secret("OPENAI_API_KEY")))
    """
    import anthropic
    client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))
    r = client.messages.create(
        model=MODELLO,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.content[0].text


SPIEGAZIONE_SIMULATA = {
    "Italiano": r"""
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
""",
    "English": r"""
#### 1. Formal Definition and Theoretical Framework
The topic is a cornerstone of economics courses. It describes how economic agents (firms, consumers, institutions) make optimal decisions under scarce resources or budget constraints.

#### 2. Key Formulas and Analytical Relations
* **Optimality condition:** $MR = MC$ *(Marginal Revenue = Marginal Cost)*
* **Price elasticity of demand:** $E_d = \frac{\% \Delta Q}{\% \Delta P}$
* **Rule of thumb:** when demand is elastic ($|E_d| > 1$), a price cut raises Total Revenue ($TR = P \cdot Q$).

#### 3. Practical Explanation and Real-World Case
*Example:* if the price of a city bus ticket rises by 10% and ridership falls by only 2%, demand is inelastic ($|E_d| < 1$): total revenue increases, because students have few alternatives.

#### 4. ⚠️ Common Exam Traps
* Do not confuse a **movement along the curve** (change in the good's own price) with a **shift of the curve** (income, substitutes).
* Always state your assumptions (no externalities, perfect competition vs monopoly).

#### 5. 💬 Typical Oral Exam Question
*"What happens to the equilibrium if the government introduces a per-unit tax?"*

**Model answer:** the supply curve shifts up by the amount of the tax. A **deadweight loss** appears: the price paid by consumers rises while the price received by sellers falls.
""",
}


def genera_spiegazione(testo: str, lingua: str) -> str:
    if not USA_AI_REALE:
        intro = "### 📖 Spiegazione (modalità demo)" if lingua == "Italiano" else "### 📖 Explanation (demo mode)"
        return f"{intro}: {testo[:60]}\n" + SPIEGAZIONE_SIMULATA[lingua]
    if lingua == "English":
        prompt = (
            "You are a university economics tutor at the University of Pavia. "
            "Give an in-depth, structured explanation in 5 sections "
            "(1. Formal Definition, 2. Key Formulas / Math, 3. Real-World Example, "
            "4. Common Exam Traps, 5. Typical Oral Exam Question with a model answer). "
            "Use markdown and LaTeX with $...$. Answer in English.\n\n"
            f"Student's text/topic:\n{testo}"
        )
    else:
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
        return f"⚠️ Errore nella chiamata IA / AI call error: {e}"


# Banca demo di 10 domande: stesse domande e stessi indici corretti nelle due lingue.
_BANCA_IT = [
    ("Qual è la condizione di ottimalità del profitto per un'impresa in concorrenza perfetta?",
     ["Prezzo = Costo Fisso Medio", "Ricavo Marginale = Costo Marginale (MR = MC)",
      "Ricavo Totale = Costi Fissi", "Prezzo = Costo Medio Variabile"], 1,
     "In concorrenza perfetta $P = MR$: l'impresa massimizza il profitto dove $MR = MC$."),
    ("Se la domanda di un bene è rigida (|E| < 1), un aumento del prezzo comporta:",
     ["Una riduzione del ricavo totale", "La chiusura immediata dell'impresa",
      "Un aumento del ricavo totale", "Un aumento proporzionale della quantità domandata"], 2,
     "Con domanda rigida la quantità cala meno che proporzionalmente al prezzo: il Ricavo Totale sale."),
    ("La 'Perdita Secca' (Deadweight Loss) rappresenta:",
     ["Il costo di magazzino dei prodotti invenduti", "Le tasse pagate dalle imprese",
      "Il valore dei macchinari ammortizzati",
      "La riduzione del surplus totale dovuta a inefficienze o monopolio"], 3,
     "È la perdita di benessere sociale netto quando il mercato non produce la quantità efficiente."),
    ("L'inflazione è:",
     ["Un aumento generalizzato e persistente del livello dei prezzi", "Un aumento del PIL",
      "Una riduzione del tasso di disoccupazione", "Un aumento del tasso di cambio"], 0,
     "L'inflazione misura la crescita generalizzata e continua dei prezzi nel tempo."),
    ("Il PIL reale si differenzia da quello nominale perché:",
     ["Esclude le esportazioni", "È misurato a prezzi costanti, depurato dall'inflazione",
      "Include solo beni durevoli", "È calcolato in valuta estera"], 1,
     "Il PIL reale usa prezzi di un anno base, così confronta la produzione senza l'effetto dei prezzi."),
    ("Il costo opportunità di una scelta è:",
     ["Il costo monetario sostenuto", "Il costo fisso di produzione",
      "Il valore della migliore alternativa a cui si rinuncia",
      "La differenza tra ricavi e costi"], 2,
     "Misura ciò a cui si rinuncia scegliendo un'opzione invece della migliore alternativa."),
    ("Una riduzione dei tassi di interesse da parte della banca centrale tende a:",
     ["Ridurre investimenti e consumi", "Stimolare investimenti e domanda aggregata",
      "Aumentare in modo permanente il valore della valuta", "Azzerare l'inflazione"], 1,
     "Tassi più bassi riducono il costo del credito e tendono a stimolare investimenti e consumi."),
    ("Nel bilancio d'esercizio l'uguaglianza fondamentale è:",
     ["Attivo = Passivo + Patrimonio netto", "Attivo = Ricavi − Costi",
      "Patrimonio netto = Passivo − Attivo", "Passivo = Attivo + Patrimonio netto"], 0,
     "Le attività (impieghi) sono finanziate da debiti (passivo) e capitale proprio (patrimonio netto)."),
    ("Rispetto alla concorrenza perfetta, un monopolista non regolamentato tende a:",
     ["Produrre di più e praticare prezzi più bassi", "Produrre meno e praticare prezzi più alti",
      "Produrre la stessa quantità", "Avere profitti sempre nulli"], 1,
     "Il monopolista restringe la quantità per alzare il prezzo, generando perdita secca."),
    ("Se aumenta il prezzo del caffè, la domanda di tè (bene sostituto) tende a:",
     ["Diminuire", "Restare invariata", "Aumentare (spostamento della curva verso destra)", "Annullarsi"], 2,
     "Per i beni sostituti, un aumento del prezzo dell'uno aumenta la domanda dell'altro."),
]

_BANCA_EN = [
    ("What is the profit-maximizing condition for a firm in perfect competition?",
     ["Price = Average Fixed Cost", "Marginal Revenue = Marginal Cost (MR = MC)",
      "Total Revenue = Fixed Costs", "Price = Average Variable Cost"], 1,
     "In perfect competition $P = MR$: the firm maximizes profit where $MR = MC$."),
    ("If the demand for a good is inelastic (|E| < 1), a price increase leads to:",
     ["A fall in total revenue", "The immediate shutdown of the firm",
      "A rise in total revenue", "A proportional fall in quantity demanded"], 2,
     "With inelastic demand quantity falls less than proportionally to price, so Total Revenue rises."),
    ("The 'Deadweight Loss' represents:",
     ["The storage cost of unsold goods", "Taxes paid by firms",
      "The value of depreciated machinery",
      "The reduction in total surplus caused by inefficiency or monopoly"], 3,
     "It is the net loss of social welfare when the market does not produce the efficient quantity."),
    ("Inflation is:",
     ["A general and sustained increase in the price level", "An increase in GDP",
      "A fall in the unemployment rate", "An increase in the exchange rate"], 0,
     "Inflation measures the general and continuous growth of prices over time."),
    ("Real GDP differs from nominal GDP because:",
     ["It excludes exports", "It is measured at constant prices, adjusted for inflation",
      "It includes only durable goods", "It is calculated in foreign currency"], 1,
     "Real GDP uses base-year prices, so it compares output without the effect of price changes."),
    ("The opportunity cost of a choice is:",
     ["The monetary cost incurred", "The fixed cost of production",
      "The value of the best alternative given up",
      "The difference between revenues and costs"], 2,
     "It measures what you give up by choosing one option over the next best alternative."),
    ("A cut in interest rates by the central bank tends to:",
     ["Reduce investment and consumption", "Stimulate investment and aggregate demand",
      "Permanently raise the value of the currency", "Eliminate inflation"], 1,
     "Lower rates reduce the cost of credit and tend to stimulate investment and consumption."),
    ("In the balance sheet, the fundamental identity is:",
     ["Assets = Liabilities + Equity", "Assets = Revenues − Costs",
      "Equity = Liabilities − Assets", "Liabilities = Assets + Equity"], 0,
     "Assets are financed by debt (liabilities) and owners' capital (equity)."),
    ("Compared with perfect competition, an unregulated monopolist tends to:",
     ["Produce more and charge lower prices", "Produce less and charge higher prices",
      "Produce the same quantity", "Always earn zero profits"], 1,
     "The monopolist restricts quantity to raise the price, creating a deadweight loss."),
    ("If the price of coffee rises, the demand for tea (a substitute) tends to:",
     ["Decrease", "Stay unchanged", "Increase (demand curve shifts right)", "Fall to zero"], 2,
     "For substitutes, a price increase of one good raises the demand for the other."),
]


def _quiz_simulato(n: int, lingua: str) -> list:
    banca = _BANCA_EN if lingua == "English" else _BANCA_IT
    indici = random.sample(range(len(banca)), min(n, len(banca)))
    quiz = []
    for k in indici:
        dom, opz, corr, spieg = banca[k]
        quiz.append({
            "domanda": dom,
            "opzioni": [f"{'ABCD'[i]}) {o}" for i, o in enumerate(opz)],
            "corretta": corr,
            "spiegazione": spieg,
        })
    return quiz


def _quiz_valido(quiz) -> bool:
    if not isinstance(quiz, list) or not quiz:
        return False
    for q in quiz:
        if not isinstance(q, dict):
            return False
        opz, corr = q.get("opzioni"), q.get("corretta")
        if not q.get("domanda") or not isinstance(opz, list) or len(opz) < 2:
            return False
        if len(set(opz)) != len(opz):
            return False
        if not isinstance(corr, int) or not (0 <= corr < len(opz)):
            return False
    return True


def genera_quiz(testo: str, n: int, lingua: str) -> list:
    if not USA_AI_REALE:
        return _quiz_simulato(n, lingua)
    if lingua == "English":
        prompt = (
            f"Create {n} multiple-choice university exam questions in economics, in English, "
            "based on the provided text (4 options, exactly 1 correct, increasing difficulty). "
            "Reply ONLY with valid JSON, no backticks or extra text, in this format:\n"
            '[{"domanda": "...", "opzioni": ["A) ...","B) ...","C) ...","D) ..."], '
            '"corretta": 0, "spiegazione": "..."}]\n'
            '"corretta" is the index (0-3) of the correct option. Keep the JSON keys in Italian as shown.\n\n'
            f"Text:\n{testo}"
        )
    else:
        prompt = (
            f"Crea {n} domande a risposta multipla d'esame universitario di Economia, in italiano, "
            "basate sul testo fornito (4 opzioni, 1 sola corretta, di difficoltà crescente). "
            "Rispondi SOLO con JSON valido, senza backtick né testo extra, nel formato:\n"
            '[{"domanda": "...", "opzioni": ["A) ...","B) ...","C) ...","D) ..."], '
            '"corretta": 0, "spiegazione": "..."}]\n'
            '"corretta" è l\'indice (0-3) dell\'opzione giusta.\n\n'
            f"Testo:\n{testo}"
        )
    try:
        raw = _chiama_llm(prompt, max_tokens=4000).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        quiz = json.loads(raw)
        if _quiz_valido(quiz):
            return quiz
    except Exception:
        pass
    st.warning("Il quiz generato dall'IA non era valido: ti mostro un quiz di esempio. / "
               "The AI quiz was not valid: showing a sample quiz.")
    return _quiz_simulato(n, lingua)

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
# SIDEBAR FOUNDER (metriche)
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
                  f"{voti.mean():.1f}/10" if len(voti) else "n/d", help=f"{len(voti)} voti")
        st.metric("Gradimento (voti ≥ 7)",
                  f"{(voti >= 7).mean() * 100:.0f}%" if len(voti) else "n/d",
                  help="Quota di voti 7 o superiori")
        st.caption("Modalità IA: " + ("reale ✅" if USA_AI_REALE else "demo (nessuna API key)"))
        st.caption("Dettaglio utenti e feedback: sezione «Area Founder» in fondo alla pagina principale.")
    elif pwd:
        st.error("Password errata")

# ----------------------------------------------------------------------
# 1) ONBOARDING (Sign-Up Rate)
# ----------------------------------------------------------------------
if "utente" not in st.session_state:
    st.markdown("<h1 class='main-title'>🎓 StudySprint</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title'>Università di Pavia · Economia<br>"
                "Il tuo assistente AI per studiare: spiegazioni chiare e mock test dai tuoi appunti.<br>"
                "<i>Also available in English for MIBE, Finance and MEFI students.</i></p>",
                unsafe_allow_html=True)

    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        with st.container(border=True):
            st.subheader("Accedi a StudySprint")
            with st.form("signup"):
                nome = st.text_input("Nome")
                corso = st.selectbox("Corso di studi", CORSI)
                ok = st.form_submit_button("Entra in StudySprint", use_container_width=True)
            st.caption("Prototipo universitario: nome, corso e voti servono solo per valutare "
                       "l'utilità dello strumento e sono visibili ai creatori del progetto.")
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
    "Incolla i tuoi appunti o indica l'argomento di studio / Paste your notes or enter a topic:",
    height=160,
    placeholder="Es. Elasticità della domanda al prezzo... / e.g. Price elasticity of demand, CAPM, portfolio theory...",
)

col_a, col_b = st.columns(2)
with col_a:
    lingua = st.radio(
        "Lingua dell'IA / AI language", LINGUE, horizontal=True,
        index=1 if utente["corso"] in CORSI_INGLESE else 0,
        key="lingua_sel",
    )
with col_b:
    n_domande = st.select_slider("Numero di domande del Mock Test", options=OPZIONI_N_DOMANDE, value=5)

c1, c2 = st.columns(2)
btn_spiega = c1.button("💡 Spiega questo concetto / Explain this concept", use_container_width=True)
btn_quiz = c2.button("📝 Genera Mock Test / Generate Mock Test", use_container_width=True)

if (btn_spiega or btn_quiz) and not testo.strip():
    st.warning("Inserisci prima un argomento o incolla i tuoi appunti. / Please enter a topic or paste your notes first.")
elif btn_spiega:
    with st.spinner("Sto preparando la spiegazione... / Preparing the explanation..."):
        st.session_state.spiegazione = genera_spiegazione(testo, lingua)
    st.session_state.update(tipo="spiegazione", output_id=str(uuid.uuid4()), feedback_dato=False)
    salva_evento("spiegazione", dettaglio=lingua)
elif btn_quiz:
    with st.spinner("Sto generando il mock test... / Generating the mock test..."):
        st.session_state.quiz = genera_quiz(testo, n_domande, lingua)
    st.session_state.update(tipo="quiz", quiz_completato=False, punteggio=None,
                            output_id=str(uuid.uuid4()), feedback_dato=False)
    salva_evento("quiz_generato", str(len(st.session_state.quiz)), dettaglio=lingua)

# ----------------------------------------------------------------------
# 3) OUTPUT IA (Quiz Completion Rate)
# ----------------------------------------------------------------------
st.divider()

if st.session_state.tipo == "spiegazione":
    with st.container(border=True):
        st.markdown(st.session_state.spiegazione)

elif st.session_state.tipo == "quiz":
    st.subheader(f"📝 Mock Test ({len(st.session_state.quiz)})")
    quiz = st.session_state.quiz
    oid = st.session_state.output_id

    if not st.session_state.quiz_completato:
        with st.form(f"quiz_{oid}"):
            risposte = []
            for i, q in enumerate(quiz):
                r = st.radio(f"**{i + 1}. {q['domanda']}**", q["opzioni"],
                             index=None, key=f"q_{oid}_{i}")
                risposte.append(r)
            invia = st.form_submit_button("Invia risposte / Submit answers")
        if invia:
            if any(r is None for r in risposte):
                st.warning("Rispondi a tutte le domande prima di inviare. / Answer all questions before submitting.")
            else:
                punti = sum(q["opzioni"].index(r) == q["corretta"] for q, r in zip(quiz, risposte))
                st.session_state.punteggio = (punti, len(quiz), risposte)
                st.session_state.quiz_completato = True
                salva_evento("quiz_completato", f"{punti}/{len(quiz)}")
                st.rerun()
    else:
        punti, tot, risposte = st.session_state.punteggio
        st.success(f"🏆 Punteggio / Score: {punti} / {tot}")
        for i, (q, r) in enumerate(zip(quiz, risposte)):
            giusta = q["opzioni"][q["corretta"]]
            with st.container(border=True):
                if r == giusta:
                    st.markdown(f"✅ **{i + 1}: corretto / correct**  \n{q['domanda']}  \n{r}")
                else:
                    st.markdown(f"❌ **{i + 1}: errato / wrong**  \n{q['domanda']}  \n"
                                f"_{r}_  \n**✔ {giusta}**")
                if q.get("spiegazione"):
                    st.markdown(f"💡 {q['spiegazione']}")

# ----------------------------------------------------------------------
# 4) FEEDBACK (Report Satisfaction, voto 1-10 + commento facoltativo)
# ----------------------------------------------------------------------
pronto_feedback = (
    st.session_state.tipo == "spiegazione"
    or (st.session_state.tipo == "quiz" and st.session_state.quiz_completato)
)
if pronto_feedback:
    st.divider()
    if st.session_state.feedback_dato:
        st.success("Grazie per il tuo feedback! / Thanks for your feedback! 🙏")
    else:
        with st.form(f"feedback_{st.session_state.output_id}"):
            voto = st.slider(
                "Quanto è stato utile questo strumento per il tuo studio? / "
                "How useful was this tool for your studying?", 1, 10, 7)
            commento = st.text_area("Commento (facoltativo) / Comment (optional)", height=80,
                                    placeholder="Cosa ti è piaciuto o cosa miglioreresti? / What did you like or what would you improve?")
            inv = st.form_submit_button("Invia valutazione / Submit rating")
        if inv:
            salva_evento("feedback", str(voto), dettaglio=st.session_state.tipo,
                         commento=commento.strip())
            st.session_state.feedback_dato = True
            st.rerun()

# ----------------------------------------------------------------------
# 5) AREA FOUNDER IN PAGINA: chi risponde e se gli piace
# ----------------------------------------------------------------------
st.divider()
with st.expander("🔒 Area Founder: utenti e feedback"):
    pwd2 = st.text_input("Password Founder", type="password", key="admin_pwd_main")
    if pwd2 == get_secret("ADMIN_PASSWORD", "founder"):
        df = carica_eventi()
        if df.empty:
            st.info("Ancora nessun dato.")
        else:
            tab1, tab2, tab3 = st.tabs(["👥 Chi sta rispondendo", "⭐ Feedback e commenti", "🗂 Dati grezzi"])

            with tab1:
                st.dataframe(riepilogo_utenti(df), use_container_width=True, hide_index=True)

            with tab2:
                fb = df[df["evento"] == "feedback"].copy()
                if fb.empty:
                    st.info("Nessun voto ricevuto.")
                else:
                    fb["Voto"] = pd.to_numeric(fb["valore"], errors="coerce")
                    fb["Gradimento"] = fb["Voto"].apply(etichetta_gradimento)
                    fb["Strumento"] = fb["dettaglio"].replace(
                        {"spiegazione": "Spiegazione", "quiz": "Mock Test"})
                    st.dataframe(
                        fb[["timestamp", "nome", "corso", "Strumento", "Voto", "Gradimento", "commento"]]
                        .rename(columns={"timestamp": "Data", "nome": "Nome",
                                         "corso": "Corso", "commento": "Commento"})
                        .sort_values("Data", ascending=False),
                        use_container_width=True, hide_index=True)

            with tab3:
                st.dataframe(df.tail(100), use_container_width=True, hide_index=True)
                st.download_button("📥 Scarica CSV completo", df.to_csv(index=False),
                                   "studysprint_eventi.csv", "text/csv")
    elif pwd2:
        st.error("Password errata")
