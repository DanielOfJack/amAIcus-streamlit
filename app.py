import os
import streamlit as st
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from display import display_full_law
from sidebar import display_sidebar

# Location codes mapping
LOCATION_CODES = {
    "Any": "",
    "City of Cape Town, South Africa": "za-cpt",
    "Johannesburg, South Africa": "za-jhb",
    "eThekwini, South Africa": "za-eth"
}

# Initialize OpenAI Embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Initialize Pinecone
pinecone_api_key = os.environ.get("PINECONE_API_KEY")
pc = Pinecone(api_key=pinecone_api_key)

index_name = "amaicus-index"
index = pc.Index(index_name)

# Initialize Pinecone Vector Store with LangChain
vector_store = PineconeVectorStore(index=index, embedding=embeddings)

# Set page configuration
st.set_page_config(page_title="amAIcus", layout="wide")

# Function to handle the search and display results
def handle_search(query, selected_location_code, selected_type):
    st.write(f"Search results for: **{query}**")
    
    # Construct metadata filter for Pinecone
    filters = {}
    if selected_location_code:
        filters["Location"] = selected_location_code
    if selected_type != "Any":
        filters["Type"] = selected_type
    
    # Query Pinecone with filters
    results = vector_store.similarity_search_with_score(
        query=query, 
        k=5, 
        filter=filters
    )
    
    # Initialize session state to store the selected document and query
    if 'selected_doc' not in st.session_state:
        st.session_state['selected_doc'] = None
    if 'selected_query' not in st.session_state:
        st.session_state['selected_query'] = None

    for i, (result, score) in enumerate(results, start=1):
        location_code = result.metadata.get("Location", "")
        title = result.metadata.get("Title", "")
        type_ = result.metadata.get("Type", "")
        date = result.metadata.get("Date", "")
        updated = result.metadata.get("Updated", "")
        doc_id = result.metadata.get("ID", "")
        content = result.page_content.split("CONTENT:", 1)[-1].strip()

        # Convert location code back to full name
        location = next(key for key, value in LOCATION_CODES.items() if value == location_code)
        
        title_formatted = title.replace("-", " ").title()

        expression_title = f"_akn_{location_code}_act_{type_}_{date}_{title}_{result.metadata.get('Language', '')}@{updated}"
        
        with st.container():
            col1, col2, col3 = st.columns([1, 4, 1])
            
            with col1:
                st.markdown(f"<h1 style='font-size: 60px;'>{score:.2f}</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size: 12px; color: grey;'>similarity score</p>", unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"**{location}**")
                st.markdown(f"### <a href='/?expression_title={expression_title}'>{title_formatted}, {type_}, {date}</a>", unsafe_allow_html=True)
                st.markdown(f"*{doc_id}*")
                st.markdown(f"{content}")
            
            with col3:
                if st.button("Show More", key=f"show_more_{i}"):
                    st.session_state['selected_doc'] = result
                    st.session_state['selected_query'] = query

            st.markdown("---")

    # Display the sidebar with additional details if a document is selected
    if st.session_state['selected_doc']:
        display_sidebar(st.session_state['selected_doc'], st.session_state['selected_query'])

# Main search interface
def main_search_page():
    # Logo and title in the header
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("assets/logo.png", use_column_width=True)  # Adjust path as needed
    with col2:
        st.title("African Legislation Search Engine")
        st.subheader("Find relevant laws and regulations")

    # Search bar input
    query = st.text_input("", placeholder="Search for laws, regulations, etc...")

    # Filters for Location and Type arranged horizontally
    col1, col2 = st.columns(2)

    with col1:
        location = st.selectbox(
            "Select Location:",
            list(LOCATION_CODES.keys())
        )
        selected_location_code = LOCATION_CODES[location]
    
    with col2:
        type_options = ["Any", "by-law", "case-law"]
        selected_type = st.radio("Select Type:", type_options)
    
    if query:
        handle_search(query, selected_location_code, selected_type)

if "expression_title" in st.query_params:
    display_full_law(st.query_params["expression_title"])
else:
    main_search_page()