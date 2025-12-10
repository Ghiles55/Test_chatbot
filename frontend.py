import streamlit as st
from backend import ask_pablo, read_file
import time
import json

st.set_page_config(page_title="Pablo – Le Parrain du Chatbot", page_icon="🕶️")

# -------------------------
# 1. INITIALISATION DE LA MÉMOIRE (Dé-commenté et sécurisé)
# -------------------------
if "messages" not in st.session_state:
    # On initialise avec le system prompt s'il existe, sinon liste vide
    try:
        sys_content = read_file("./context.txt")
    except:
        sys_content = "Tu es un assistant utile."  # Fallback si le fichier n'existe pas

    st.session_state.messages = [
        {"role": "system", "content": sys_content}
    ]

st.title("🕶️ Test - Chatbot JSON")
st.write("Chargez un fichier JSON pour l'analyser.")

# -------------------------
# 2. AFFICHAGE DE L’HISTORIQUE
# -------------------------
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            # Si le contenu ressemble à du JSON, on tente de l'afficher proprement
            try:
                # On vérifie si c'est un JSON valide pour l'affichage pretty
                json_data = json.loads(msg["content"])
                st.json(json_data)
            except:
                st.write(msg["content"])

# -------------------------
# 3. ZONE D'UPLOAD DE FICHIER
# -------------------------
uploaded_file = st.file_uploader("Importer un fichier JSON", type=["json"])

if uploaded_file:
    try:
        # Lecture et conversion du fichier JSON en dictionnaire Python
        json_data = json.load(uploaded_file)
        # Conversion en chaîne de caractères pour l'envoi au LLM
        json_string = json.dumps(json_data, indent=2, ensure_ascii=False)

        # --- VERIFICATION ANTI-DOUBLON ---
        # On regarde le dernier message utilisateur pour voir si c'est le même contenu.
        # Cela évite que le bot réponde en boucle à chaque rafraîchissement de page.
        last_user_msg = None
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "user":
                last_user_msg = msg["content"]
                break

        # Si le contenu est nouveau, on traite
        if last_user_msg != json_string:

            # Ajout à la mémoire
            st.session_state.messages.append({"role": "user", "content": json_string})

            # Affichage immédiat du fichier uploadé dans le chat
            with st.chat_message("user"):
                st.json(json_data)

            # -------------------------
            # 4. APPEL AU BACKEND GROQ
            # -------------------------
            with st.chat_message("assistant"):
                placeholder = st.empty()
                full_response = ""

                # Envoi au backend
                # Note: Assure-toi que ask_pablo gère bien les gros textes si le JSON est volumineux
                stream = ask_pablo(chat_history=st.session_state.messages)

                # Lecture du stream
                for chunk in stream:
                    # Gestion des différents types de réponses (selon la lib utilisée : openai, groq, etc.)
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
                        placeholder.write(full_response)

                    # Petit délai pour effet visuel (optionnel, peut être retiré pour plus de vitesse)
                    time.sleep(0.005)

                    # Sauvegarde de la réponse assistant
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )

    except json.JSONDecodeError:
        st.error("Le fichier uploadé n'est pas un JSON valide.")
    except Exception as e:
        st.error(f"Une erreur s'est produite : {e}")