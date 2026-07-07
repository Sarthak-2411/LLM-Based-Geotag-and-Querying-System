import streamlit as st
import pandas as pd
import os
import json
import re
from google import genai
from dotenv import load_dotenv
from streamlit_folium import st_folium
import folium
from google.genai import types
load_dotenv()   
# from google import genai
GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
MODEL_ID = os.getenv("MODEL_ID")
client = genai.Client(api_key=GEMINI_API_KEY)

prompt = """
You are a specialized Geotagging and Mapping system for India. 
    Your task is to process input text and extract location entities 
    following these strict rules:
    
    1. Scope Limitation:
    - Only extract locations that are within India. Ignore any foreign locations.
    - Only extract the locations where the disaster or event has taken place.
    
    2. Coding Standards:
    - Districts should use official English names from Census of India.
    -  If a smaller location (city, town, village) appears along with a larger location (district, state),
       resolve them together as "City, State". Do not give the larger location as separate location.
    
    Respond ONLY as a JSON list of strings.
"""
def extract_location(text: str):
    # ask = ("Extract every place-name (city, district, state, country, landmark, facility, "
    #        "river, etc.) mentioned in the text. Respond ONLY as a JSON list of strings.")
    try:
        response = client.models.generate_content(
            model="gemma-4-31b-it",
            contents=text,
            config=types.GenerateContentConfig(system_instruction=prompt)
        )
        print(response.text)
        text = re.sub(r"^```(?:json)?\s*", "", response.text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)[0]
    except Exception:
        print("Exception "+text)
        return "[]"
    # try:
    #     r = GEM.generate_content(ask + "\n\n" + text,
    #           generation_config={"temperature":0.0, "max_output_tokens":256})
    #     return json.loads(r.text)
    # except Exception:
    #     print("Exception "+ text)
    #     return re.findall(r"\b[A-Z][A-Za-z .'-]{3,}", text)[:10]


from geopy.geocoders import Nominatim
_geo = Nominatim(user_agent="geoLLM-dashboard", timeout=10)
@st.cache_data(show_spinner=False)
def geocode(loc: str):    
    try:
        r = _geo.geocode(loc, addressdetails=True)  # fetch with address metadata
        if r and "country" in r.raw["address"]:
            if r.raw["address"]["country"] == "India":   # ✅ restrict to India
                return (r.latitude, r.longitude)
        return (None, None)  # skip if not in India
    except Exception:
        return (None, None)
##
if "DATAFRAME" not in st.session_state:
    st.session_state.DATAFRAME = None
# DATAFRAME = st.session_state.DATAFRAME

##
st.set_page_config("LLM based Geotagging, Mapping and Query System using RAG", layout="wide")

# Side Bar
st.sidebar.title("Controls")
uploaded_file = st.sidebar.file_uploader("Choose an .xlsx file", type=["xlsx"])

if uploaded_file is None:
    st.session_state.DATAFRAME = None
if uploaded_file is not None and st.session_state.DATAFRAME is None:
    df = pd.read_excel(uploaded_file, header=None, names=['text', 'date', 'time', 'link','temp'])
    df = df.drop('temp', axis=1)
    
    df['date'] = df['date'].astype(str).str.strip()
    df.drop(columns=['time'], inplace=True)
    df.drop(columns=['link'], inplace=True)

    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    N = 5
    # DATAFRAME = df.head(N)
    # DATAFRAME = df.sample(n=N, random_state=56)
    st.session_state.DATAFRAME  = df.sample(n=N, random_state=56)
   
    dmin, dmax = df['date'].min(), df['date'].max()

    ##############
from pathlib import Path
from newspaper import Article
import uuid
CACHE_DIR = Path(".raw_articles"); CACHE_DIR.mkdir(exist_ok=True)
def fetch_article(url: str) -> str:
    cache = CACHE_DIR / (uuid.uuid5(uuid.NAMESPACE_URL, url).hex + ".txt")
    if cache.exists(): return cache.read_text("utf8")
    art = Article(url); art.download(); art.parse()
    cache.write_text(art.text, "utf8"); return art.text
from datetime import datetime
import re
from dateutil import parser as dparse

def article_to_row(text: str):
    # Default to current date/time
    dt = datetime.now()

    # Try to extract a date from the text
    m = re.search(r"\b(\d{1,2}\s+\w+\s+\d{4})\b", text)
    if m:
        try:
            dt = dparse.parse(m.group(1), dayfirst=True)
        except Exception:
            pass

    return {
        "text": text,
        "date": dt
    }
if st.session_state.DATAFRAME is not None:
    with st.sidebar.form("urlform"):
        new_url = st.text_input("Paste news URL")
        if st.form_submit_button("Ingest"):
            try:
                with st.spinner("Fetching article …"):
                    art_txt = fetch_article(new_url.strip())
                if len(art_txt) < 200:
                    st.warning("Article too short."); st.stop()

                new_row = pd.DataFrame([article_to_row(art_txt)])
                st.session_state.DATAFRAME = pd.concat([st.session_state.DATAFRAME, new_row], ignore_index=True)
                st.sidebar.success("Article added!")
            except Exception as e:
                st.sidebar.exception(e)
        # print(dmin, dmax)
        # date_range = st.sidebar.date_input("Date range", [dmin, dmax])

# Main Page
st.title("Indian Disaster Dashboard")
# Tabs
# tabs = st.tabs(["Overview", "Map", "Temporal Analysis", "Chat With LLM"])
tabs = st.tabs(["Overview", "Map", "Chat With LLM"])

with tabs[0]:
    if st.session_state.DATAFRAME is not None:        
        if st.button("Start Geotagging"):
            with st.spinner("Thinking..."):
                print("Calling LLM")
                st.session_state.DATAFRAME['location'] = st.session_state.DATAFRAME['text'].apply(extract_location)
                st.session_state.DATAFRAME[["lat","lon"]] = st.session_state.DATAFRAME["location"].apply(lambda x: pd.Series(geocode(x)))
                    # else pd.Series([None, None]))
                #calling llm
        st.dataframe(st.session_state.DATAFRAME,  use_container_width=True)
    else:
        st.subheader("Please Upload Dataset first")

with tabs[1]:
    if st.session_state.DATAFRAME is None:
        st.subheader("Please Upload the Dataset and Geotag it first")
    elif 'location' not in st.session_state.DATAFRAME.columns: # If text is not geotagged
        st.subheader("Please geotag the Dataset")
    else:        
        fmap = folium.Map(zoom_start=4)
        geojson = folium.GeoJson("states_india.geojson", style_function=lambda feature: {
            "fillOpacity": 0,
            "color": "black",
            "weight": 2,
        })
        geojson.add_to(fmap)
        from folium.plugins import MarkerCluster

        marker_cluster = MarkerCluster().add_to(fmap)

        for _, row in st.session_state.DATAFRAME.dropna(subset=["lat","lon"]).iterrows():
            folium.Circle(
                    [row.lat, row.lon],
                    radius= 3000,#get_radius(r.disaster_type),
                    # color=get_colour(r.disaster_type),
                    fill=True, fill_opacity=0.4,
                    popup=folium.Popup(f"""
                        <b>Date:</b> {row.date.date()}<br>
                        <b>Location:</b> {row.location}
                    """, max_width=250),
                ).add_to(marker_cluster)
        # Automatically zoom to India
        # <b>{row.event}</b><br>
        #                 <b>Date:</b> {row.date.date()}<br>
        #                 <b>Type:</b> {row.disaster_type}<br>
        #                 <b>Location:</b> {row.location}
        
        st_folium(fmap, width=900, height=550, key="map", returned_objects=[])


################
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import torch
from google.genai import types
@st.cache_resource
def load_model():
    print("Loading Transformer...")
    return SentenceTransformer("all-MiniLM-L6-v2")
    # return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    print("Transformer Loaded Successfully !")

@st.cache_resource
def load_data_and_index():
    print("Loading resources...")
    index = faiss.read_index("indexes/news_faiss.index")
    with open("indexes/news_metadata.pkl", "rb") as f:
        metadata = pickle.load(f)
    with open("indexes/news_documents.pkl", "rb") as f:
        documents = pickle.load(f)
    print("Resources Loaded Successfully !")
    return index, metadata, documents
#RAG CHAT
with tabs[2]:
    model = load_model()
    index, metadata, documents = load_data_and_index()
    def retrieve(query, k=5):
        with torch.no_grad():
            q_embed = model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True
            ).astype("float32")
            D, I = index.search(q_embed, k=6)

            retrieved_docs = set()
            context = []
            context = [metadata[i]["text"] for i in I[0]]
            # for idx in I[0]:
            #     retrieved_docs.add(metadata[idx]["doc_id"])
            # for doc_id in retrieved_docs:
            #     context.append(documents[doc_id])
            return context
            # print("\n\n".join(context))
            # print(len(context))
    def generate_answer(query, context):
        ask = ("Extract every place-name (city, district, state, country, landmark, facility, "
           "river, etc.) mentioned in the text. Respond ONLY as a JSON list of strings.")
        try:
            response = client.models.generate_content(
                model="gemma-4-31b-it",
                contents=f"QUERY: {query} \n\n CONTEXT: {context}",
                config=types.GenerateContentConfig(system_instruction="""You are GEOLLM. Your task is to answer the QUERY given by the user based on the information
        provided by the CONTEXT given by the user after. You are not allowed to use data outside the CONTEXT. If the answer to the query is not 
        available on the CONTEXT, then just say that you do not have the data. The QUERY and the CONTEXT will be given by the user""")
            )
            return response.text
        except Exception:
            print("Some Error has occured")
            return "Error Please try again!"   


    st.title("RAG-based Disaster News Chatbot")
    st.markdown("Ask questions...")
    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # User input
    query = st.chat_input("Ask something...")

    if query:
        # Store user message
        st.session_state.messages.append({"role": "user", "content": query})

        with st.chat_message("user"):
            st.markdown(query)

        # Retrieve context
        retrieved_chunks = retrieve(query)
        context = "\n\n".join(retrieved_chunks)
        # print(context)
        # Generate answer
        answer = generate_answer(query, context)

        # Store response
        st.session_state.messages.append({"role": "assistant", "content": answer})

        with st.chat_message("assistant"):
            st.markdown(answer)

        # Optional: show sources
        with st.expander("Retrieved Context:"):
            for i, chunk in enumerate(retrieved_chunks):
                st.text(f"**Chunk {i+1}:**\n{chunk}\n---")