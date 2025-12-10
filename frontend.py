import streamlit as st
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
    # st.rerun()