import os
import streamlit as st
from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from sidebar import display_sidebar
from openai import OpenAI
import re

st.set_page_config(
    page_title="amAIcus",
    layout="wide",  # Use wide mode
)

# Location codes mapping
LOCATION_CODES = {
    "Any": "",
    "City of Cape Town, South Africa": "za-cpt",
    "Johannesburg, South Africa": "za-jhb",
    "eThekwini, South Africa": "za-eth",
    "Eastern Cape": "za-ec443",
    "Western Cape Region 1": "za-wc011",
    "Western Cape Region 33": "za-wc033"
}

term_mapping = {
    "subsec": "Subsection",
    "sec": "Section",
    "para": "Paragraph",
    "att": "Attachment",
    "part": "Part"
}

# Initialize OpenAI Embeddings and GPT-4o Mini
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
gpt_client = OpenAI()  # Initialize the GPT client

# Initialize Pinecone
pinecone_api_key = os.environ.get("PINECONE_API_KEY")
pc = Pinecone(api_key=pinecone_api_key)

index_name = "amaicus-index"
index = pc.Index(index_name)

# Initialize Pinecone Vector Store with LangChain
vector_store = PineconeVectorStore(index=index, embedding=embeddings)


def transform_component_id(component_id):
    # Step 1: Replace double underscores with commas
    component_id = component_id.replace("__", ", ")
    
    # Step 2: Replace single underscores with spaces
    component_id = component_id.replace("_", " ")
    
    # Step 3: Remove trailing __p_{digit} if present
    component_id = re.sub(r", p \d+$", "", component_id)
    
    # Step 4: Map the terms to their reader-friendly equivalents
    # Use regular expression with word boundaries to ensure accurate replacements
    for key, value in term_mapping.items():
        component_id = re.sub(rf"\b{key}\b", value, component_id)
    
    return component_id

# Function to modify the query using GPT-4o Mini (HyDE approach)
def modify_query_with_gpt(query):
    prompt = f"""
    You are a research assistant responsible for helping locate relevant legal information. Please take the user's query or statement and refine it for use in a embedded vector search.

    Query/statement: {query}

    Your response should be clear and clinical. Return only the updated query.
    """

    # Send the prompt to GPT-4o Mini
    response = gpt_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    
    # Access the content of the first choice
    return response.choices[0].message.content.strip()

def handle_search(query, selected_location_code, selected_type):
    # Check if the search has already been performed
    if query != st.session_state.get('last_query', ''):
        # Modify the query using GPT-4o Mini (HyDE approach)
        modified_query = modify_query_with_gpt(query)
        st.write(f"Search results for: **{query}** (modified to: **{modified_query}**)")

        # Construct metadata filter for Pinecone
        filters = {}
        if selected_location_code:
            filters["Location"] = selected_location_code
        if selected_type != "Any":
            filters["Type"] = selected_type
        
        # Query Pinecone with the modified query
        results = vector_store.similarity_search_with_score(
            query=modified_query, 
            k=5, 
            filter=filters
        )

        # Save the results and the query in session state
        st.session_state['search_results'] = results
        st.session_state['last_query'] = query

    else:
        # Use the results stored in session state
        results = st.session_state['search_results']

    # Initialize session state to store the selected document and query
    if 'selected_doc' not in st.session_state:
        st.session_state['selected_doc'] = None
    if 'selected_query' not in st.session_state:
        st.session_state['selected_query'] = None

    # Display the search results
    for i, (result, score) in enumerate(results, start=1):
        location_code = result.metadata.get("Location", "")
        title = result.metadata.get("Title", "")
        type_ = result.metadata.get("Type", "")
        date = result.metadata.get("Date", "")
        updated = result.metadata.get("Updated", "")
        doc_id = result.metadata.get("ID", "")
        content = result.page_content

        # Extract the section between HEADINGS and CONTENT, but skip to the first line after CROSS if it exists
        pattern = r"HEADINGS:[^\n]*\n(?:CROSS[^\n]*\n)?(.*?)CONTENT:"
        headings_match = re.search(pattern, content, re.DOTALL)
        headings_text = headings_match.group(1).strip() if headings_match else ""

        # Extract text after CONTENT
        content_text = content.split("CONTENT:", 1)[-1].strip()

        # Convert location code back to full name
        location = next((key for key, value in LOCATION_CODES.items() if value == location_code), location_code)
        
        title_formatted = title.replace("-", " ").title()

        expression_title = f"akn_{location_code}_act_{type_}_{date}_{title}_{result.metadata.get('Language', '')}@{updated}"
        
        # Construct the URL for the hyperlink
        url_path = expression_title.replace('_', '/')
        full_url = f"https://openbylaws.org.za/{url_path}"
                
        with st.container():
            col1, col2, col3 = st.columns([1, 4, 1])
            
            with col1:
                st.markdown(f"<h1 style='font-size: 80px;'>{score:.2f}</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size: 20px; color: grey;'>similarity score</p>", unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"**{location}**")
                st.markdown(f"### <a href='{full_url}' target='_blank'>{title_formatted}, {type_}, {date}</a>", unsafe_allow_html=True)
                st.markdown(f"<a href='{full_url}#{doc_id}' target='_blank'>{transform_component_id(doc_id)}</a>", unsafe_allow_html=True)
                st.markdown(f"{headings_text}")
                st.markdown(f"{content_text}")
            
            with col3:
                if st.button("AI Summary", key=f"show_more_{i}"):
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

main_search_page()