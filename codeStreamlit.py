import streamlit as st
# Cette fonction doit être le TOUT premier appel à Streamlit
# Aucun code Streamlit ne doit apparaître avant cette ligne
st.set_page_config(page_title="Multi-Requête OpenAI", layout="wide")

# Importez les autres bibliothèques APRÈS le set_page_config
import pandas as pd
import time
import re
from openai import OpenAI

# Maintenant le titre et le reste du code
st.title("💬 Multi-Requête OpenAI avec Export CSV")

# === Initialisation session_state pour accumuler les résultats ===
if "results" not in st.session_state:
    st.session_state.results = []
if "key_validated" not in st.session_state:
    st.session_state.key_validated = False

# === INPUTS ===
with st.expander("⚙️ Configuration", expanded=not st.session_state.key_validated):
    api_key = st.text_input("🔑 Entrez votre clé API OpenAI", type="password")
    
    # Bouton de validation de la clé API
    if st.button("✅ Valider la clé API") and api_key:
        # Vérification basique du format de la clé API
        if re.match(r'^sk-[A-Za-z0-9]{20,}$', api_key):
            try:
                # Test de la clé API avec une requête minimale
                client = OpenAI(api_key=api_key)
                client.models.list()
                st.session_state.key_validated = True
                st.session_state.api_key = api_key  # Stockage temporaire sécurisé
                st.success("✅ Clé API validée avec succès!")
            except Exception as e:
                st.error(f"❌ Erreur de validation: {str(e)}")
        else:
            st.error("❌ Format de clé API invalide. Elle doit commencer par 'sk-' suivi de 48 caractères.")

# Si la clé est validée, afficher le reste de l'interface
if st.session_state.key_validated:
    prompt_text = st.text_area("📝 Texte de la requête à envoyer", height=100)
    num_requests = st.number_input("🔁 Nombre de répétitions", min_value=1, max_value=20, value=3, 
                                help="Limité à 20 pour éviter de dépasser les quotas")
    
    model_options = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    selected_model = st.selectbox("🤖 Modèle à utiliser", model_options)
    
    col1, col2 = st.columns(2)
    start_button = col1.button("🚀 Lancer les requêtes")
    reset_button = col2.button("🗑️ Réinitialiser les résultats")

    # === Logique : envoi de requêtes ===
    if start_button and prompt_text:
        with st.spinner(f"Envoi de {num_requests} requêtes..."):
            progress_bar = st.progress(0)
            
            for i in range(num_requests):
                try:
                    # Utilisation de la nouvelle API OpenAI
                    client = OpenAI(api_key=st.session_state.api_key)
                    response = client.chat.completions.create(
                        model=selected_model,
                        messages=[{"role": "user", "content": prompt_text}]
                    )
                    answer = response.choices[0].message.content
                    
                    st.session_state.results.append({
                        "requête": prompt_text,
                        "modèle": selected_model,
                        "réponse": answer
                    })
                    
                    # Mise à jour de la barre de progression
                    progress_bar.progress((i + 1) / num_requests)
                    
                    # Attente avec backoff exponentiel pour respecter les limites de l'API
                    wait_time = 1 + (i * 0.2)  # Augmente légèrement le temps d'attente à chaque requête
                    with st.spinner(f"Pause de {wait_time:.1f}s avant la prochaine requête..."):
                        time.sleep(wait_time)
                        
                except Exception as e:
                    st.session_state.results.append({
                        "requête": prompt_text,
                        "modèle": selected_model,
                        "réponse": f"Erreur : {str(e)}"
                    })
                    st.error(f"Erreur à la requête {i+1}: {str(e)}")
            
            # Nettoyage de la clé API de la mémoire une fois terminé
            if "api_key" in st.session_state:
                del st.session_state["api_key"]
                
            st.success(f"✅ {num_requests} requêtes envoyées avec succès!")

    # === Réinitialiser les résultats ===
    if reset_button:
        st.session_state.results = []
        st.success("🗑️ Résultats réinitialisés.")

    # === Affichage et téléchargement ===
    if st.session_state.results:
        st.subheader(f"📊 Résultats ({len(st.session_state.results)} requêtes)")
        df = pd.DataFrame(st.session_state.results)
        
        # Affichage des résultats avec onglets
        tab1, tab2 = st.tabs(["📋 Aperçu", "📊 Données complètes"])
        
        with tab1:
            # Afficher un aperçu plus court des réponses
            df_preview = df.copy()
            df_preview['réponse'] = df_preview['réponse'].str[:100] + '...'
            st.dataframe(df_preview)
            
        with tab2:
            # Afficher toutes les données
            st.dataframe(df)
        
        # Option d'export
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger en CSV",
            data=csv,
            file_name='resultats_openai.csv',
            mime='text/csv'
        )
        
        # Ajouter une option pour effacer la clé API de la session
        if st.button("🔒 Déconnecter (effacer la clé API)"):
            st.session_state.key_validated = False
            st.experimental_rerun()
