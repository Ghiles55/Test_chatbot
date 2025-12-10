'''import streamlit as st
from backend import ask_pablo, read_file
import time
import json

st.set_page_config(page_title="Pablo – Le Parrain du Chatbot", page_icon="🕶️")

# -------------------------
# 1. INITIALISATION DE LA MÉMOIRE
# -------------------------
if "messages" not in st.session_state:
    try:
        sys_content = read_file("./context.txt")
    except:
        sys_content = "Tu es un assistant expert en analyse de données JSON."

    st.session_state.messages = [
        {"role": "system", "content": sys_content}
    ]

st.title("🕶️ Test - Chatbot Multi-JSON")
st.write("Chargez un ou plusieurs fichiers JSON, puis validez pour lancer l'analyse.")

# -------------------------
# 2. AFFICHAGE DE L’HISTORIQUE
# -------------------------
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            # On tente d'afficher proprement les JSONs
            try:
                # Si le message commence par [ ou {, c'est probablement du JSON
                if msg["content"].strip().startswith(("{", "[")):
                    json_data = json.loads(msg["content"])
                    # On met le JSON dans un expander pour ne pas polluer visuellement le chat
                    with st.expander("Voir le contenu JSON envoyé"):
                        st.json(json_data)
                else:
                    st.write(msg["content"])
            except:
                st.write(msg["content"])

# -------------------------
# 3. ZONE D'UPLOAD MULTIPLE & VALIDATION
# -------------------------

# Création d'un formulaire ou d'une zone conteneur pour regrouper upload + bouton
with st.container():
    # accept_multiple_files=True renvoie une LISTE de fichiers
    uploaded_files = st.file_uploader(
        "Importer vos fichiers JSON",
        type=["json"],
        accept_multiple_files=True
    )

    # Le bouton sert de "déclencheur" pour éviter que le LLM ne parte au quart de tour
    send_button = st.button("Lancer l'analyse 🚀", disabled=(not uploaded_files))

# -------------------------
# 4. TRAITEMENT LORS DU CLIC
# -------------------------
if send_button and uploaded_files:

    combined_data = []

    # Barre de progression (optionnel, sympa si beaucoup de fichiers)
    progress_bar = st.progress(0)

    try:
        # On boucle sur tous les fichiers uploadés
        for i, file in enumerate(uploaded_files):
            file_content = json.load(file)
            # On structure les données pour que le LLM sache quel contenu vient de quel fichier
            combined_data.append({
                "filename": file.name,
                "content": file_content
            })
            progress_bar.progress((i + 1) / len(uploaded_files))

        progress_bar.empty()  # On retire la barre une fois fini

        # Conversion de la liste globale en string JSON
        json_string = json.dumps(combined_data, indent=2, ensure_ascii=False)

        # Ajout à la mémoire (côté User)
        st.session_state.messages.append({"role": "user", "content": json_string})

        # Affichage immédiat dans le chat
        with st.chat_message("user"):
            st.write(f"📂 **{len(uploaded_files)} fichiers envoyés**")
            with st.expander("Détails des données envoyées"):
                st.json(combined_data)

        # -------------------------
        # APPEL AU BACKEND GROQ
        # -------------------------
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            # Indicateur visuel pendant l'attente
            with st.spinner('Pablo analyse les documents...'):
                stream = ask_pablo(chat_history=st.session_state.messages)

            # Lecture du stream
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    placeholder.write(full_response)
                time.sleep(0.005)

            # Sauvegarde de la réponse assistant
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )

    except json.JSONDecodeError:
        st.error("L'un des fichiers n'est pas un JSON valide.")
    except Exception as e:
        st.error(f"Erreur lors du traitement : {e}")

    # Optionnel : Rerun pour nettoyer l'uploader visuellement (si souhaité)
    # st.rerun()'''
import streamlit as st
from backend import ask_pablo, read_file
import time
import json

st.set_page_config(page_title="Pablo – Analyste Séquentiel", page_icon="🕶️")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "Tu es un expert JSON."}]

st.title("🕶️ Pablo - Analyseur de gros volumes")
st.info("Mode 'Séquentiel' actif : Les fichiers sont traités un par un pour éviter la saturation mémoire.")

# --- AFFICHAGE HISTORIQUE ---
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# --- UPLOAD ---
with st.container():
    uploaded_files = st.file_uploader("Fichiers JSON", type=["json"], accept_multiple_files=True)
    user_question = st.text_input("Quelle est votre question sur ces fichiers ?", "Fais-moi un résumé global.")
    send_button = st.button("Analyser les fichiers 🚀", disabled=(not uploaded_files))

if send_button and uploaded_files:

    # 1. Barre de progression
    progress_bar = st.progress(0)
    status_text = st.empty()

    summaries = []  # On va stocker les résumés de chaque fichier ici

    # 2. BOUCLE SÉQUENTIELLE (Le secret pour ne pas crasher)
    try:
        for i, file in enumerate(uploaded_files):
            file_name = file.name
            status_text.write(f"🔍 Analyse du fichier {i + 1}/{len(uploaded_files)} : **{file_name}**...")

            # Lecture du fichier
            file_content = json.load(file)

            # On prépare un mini-prompt pour CE fichier uniquement
            # On tronque à 40k tokens par sécurité pour laisser de la place à la réponse
            json_str = json.dumps(file_content, separators=(',', ':'), ensure_ascii=False)[:160000]

            prompt_intermediaire = [
                {"role": "system", "content": "Tu es un extracteur de données. Analyse le JSON fourni."},
                {"role": "user",
                 "content": f"Voici le fichier {file_name} : {json_str}. \n\n TÂCHE : Extrais les informations pertinentes par rapport à la demande : '{user_question}'. Sois concis."}
            ]

            # Appel API pour ce fichier spécifique
            # Note : On n'utilise pas l'historique global ici pour économiser la mémoire
            response_stream = ask_pablo(chat_history=prompt_intermediaire)

            file_summary = ""
            for chunk in response_stream:
                content = chunk.choices[0].delta.content
                if content:
                    file_summary += content

            summaries.append(f"--- Résumé de {file_name} ---\n{file_summary}\n")
            progress_bar.progress((i + 1) / len(uploaded_files))

        # 3. SYNTHÈSE FINALE
        status_text.write("🧠 Synthèse de tous les fichiers en cours...")

        # On combine tous les résumés intermédiaires
        final_context = "\n".join(summaries)

        # On construit le prompt final
        final_prompt = f"J'ai analysé {len(uploaded_files)} fichiers séparément. Voici leurs résumés :\n\n{final_context}\n\nQUESTION GLOBALE : {user_question}"

        # Ajout à l'historique visible
        st.session_state.messages.append({"role": "user", "content": final_prompt})

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            # Appel API final avec le contexte digéré
            stream = ask_pablo(chat_history=[
                {"role": "system", "content": "Tu es un analyste qui synthétise plusieurs rapports."},
                {"role": "user", "content": final_prompt}
            ])

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    placeholder.write(full_response)
                time.sleep(0.005)

            st.session_state.messages.append({"role": "assistant", "content": full_response})

        status_text.empty()
        progress_bar.empty()

    except Exception as e:
        st.error(f"Une erreur est survenue : {e}")