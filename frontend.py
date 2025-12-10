import streamlit as st
from backend import ask_pablo, read_file
import time
import json
from fpdf import FPDF
import io

st.set_page_config(page_title="Pablo – Traitement Automatisé", page_icon="🕶️")

# -------------------------
# 1. CHARGEMENT DU CONTEXTE (Vos instructions maîtresses)
# -------------------------
try:
    # C'est ici que résident vos instructions (ex: "Extrais les totaux", "Cherche les erreurs", etc.)
    sys_content = read_file("./context.txt")
except:
    sys_content = "Tu es un assistant expert en analyse JSON."

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": sys_content}]

st.title("🕶️ Sonalyze - Analyse Automatisée")
st.write("Le système appliquera les instructions de votre `context.txt` à chaque fichier.")

# -------------------------
# 2. AFFICHAGE HISTORIQUE
# -------------------------
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# -------------------------
# 3. UPLOAD ET DÉCLENCHEMENT
# -------------------------
with st.container():
    uploaded_files = st.file_uploader(
        "Déposez vos fichiers JSON (Traitement séquentiel)",
        type=["json"],
        accept_multiple_files=True
    )
    # Le bouton lance directement le processus défini dans le contexte
    send_button = st.button("Lancer le traitement ⚡", disabled=(not uploaded_files))

if send_button and uploaded_files:

    progress_bar = st.progress(0)
    status_text = st.empty()
    analyses_partielles = []

    try:
        # --- ÉTAPE 1 : ANALYSE FICHIER PAR FICHIER ---
        for i, file in enumerate(uploaded_files):
            file_name = file.name
            status_text.write(
                f"⚙️ Application des instructions au fichier {i + 1}/{len(uploaded_files)} : **{file_name}**...")

            # Lecture
            file_content = json.load(file)

            # Minification pour économiser les tokens
            json_str = json.dumps(file_content, separators=(',', ':'), ensure_ascii=False)

            # On coupe si > 120k caractères (approx 30k tokens) pour garder de la place pour la réponse
            if len(json_str) > 120000:
                json_str = json_str[:120000] + "... (tronqué)"

            # --- C'est ici que la magie opère ---
            # On envoie : LE SYSTEM PROMPT + LE FICHIER
            # Le modèle va donc exécuter vos ordres sur ce fichier précis.
            messages_intermediaires = [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": f"Voici le contenu du fichier '{file_name}' à traiter : {json_str}"}
            ]

            # Appel Backend (Map)
            stream = ask_pablo(chat_history=messages_intermediaires)

            partial_res = ""
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    partial_res += content

            analyses_partielles.append(f"--- Résultat pour {file_name} ---\n{partial_res}\n")
            progress_bar.progress((i + 1) / len(uploaded_files))

        # --- ÉTAPE 2 : CONSOLIDATION FINALE ---
        status_text.write("📑 Consolidation des résultats...")

        # On regroupe toutes les analyses partielles
        global_context = "\n".join(analyses_partielles)

        # On demande au modèle de finaliser (si besoin) ou d'afficher le tout
        # On réinjecte le sys_content pour qu'il garde sa personnalité/format de sortie
        final_prompt_content = f"Voici les résultats de l'analyse individuelle de chaque fichier. Compile ou présente le résultat final conformément à tes instructions système :\n\n{global_context}"

        # Ajout à l'historique visible (User)
        st.session_state.messages.append({"role": "user", "content": "Traitement des fichiers effectué."})

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            # Appel Backend Final (Reduce)
            stream_final = ask_pablo(chat_history=[
                {"role": "system", "content": sys_content},
                {"role": "user", "content": final_prompt_content}
            ])

            for chunk in stream_final:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    placeholder.write(full_response)
                time.sleep(0.005)

            # Sauvegarde réponse
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        status_text.empty()
        progress_bar.empty()

    except Exception as e:
        st.error(f"Erreur durant le traitement : {e}")
