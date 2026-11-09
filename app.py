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
