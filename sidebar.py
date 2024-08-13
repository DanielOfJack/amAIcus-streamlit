import os
import streamlit as st
from lxml import etree
from openai import OpenAI

LOCATION_CODES = {
    "Any": "",
    "City of Cape Town, South Africa": "za-cpt",
    "Johannesburg, South Africa": "za-jhb",
    "eThekwini, South Africa": "za-eth"
}

# Function to extract the preamble from the XML document
def extract_text_ignore_remarks(element, nsmap):
    # Extracts text from the element, ignoring any text within <a:remark> elements
    return ' '.join(element.xpath(".//text()[not(ancestor::a:remark)]", namespaces=nsmap))

def extract_preamble(xml_content):
    root = etree.fromstring(xml_content)
    
    nsmap = root.nsmap
    preamble = root.find(".//preamble", namespaces=nsmap)
    
    if preamble is not None:
        return ''.join(preamble.itertext()).strip()
    
    return None

# Function to extract the section context from the XML document
def extract_section_context(xml_content, component_id):
    # Parse the XML content
    root = etree.fromstring(xml_content)
    
    # Find the component using the ID
    component = root.find(f".//*[@eId='{component_id}']")
    
    if component is None:
        return None  # If the component is not found, return None
    
    # Traverse up to find the section containing this component
    section = component.xpath('ancestor::section[1]')
    
    if section:
        # If a section is found, return its text content
        return etree.tostring(section[0], method="text", encoding="unicode").strip()
    else:
        # If no section is found, go up two levels from the component
        parent = component.getparent()
        grandparent = parent.getparent() if parent is not None else None
        
        # Combine the text from parent and grandparent (if available)
        context = ""
        if grandparent is not None:
            context += etree.tostring(grandparent, method="text", encoding="unicode").strip() + "\n"
        if parent is not None:
            context += etree.tostring(parent, method="text", encoding="unicode").strip()
        
        return context.strip()

# Function to generate a summary of the document using OpenAI
def generate_document_summary(query, title, location, date, preamble):
    client = OpenAI()

    prompt = f"""
    You are a legal assistant, helping a client to understand whether or not a legal document is relevant for what they are searching for. The client is looking for the following:

    {query}

    The following document is being reviewed for its relevance to the search query:

    {title}, {location}, {date}

    Provide the user with a concise summary of what the document pertains to based on the preamble:

    {preamble}
    """

    # Create a chat completion with streaming
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    # Collect the streamed response
    summary = ""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            summary += chunk.choices[0].delta.content

    return summary.strip()

# Function to generate a summary of the section using OpenAI
def generate_section_summary(query, title, location, date, section_context, component_id):
    client = OpenAI()

    prompt = f"""
    You are a legal assistant, helping a client to understand whether or not a legal document is relevant for what they are searching for. The client is looking for the following:

    {query}

    The following document is being reviewed for its relevance to the search query:

    {title}, {location}, {date}

    Component ID: {component_id}

    The component ID regards the specific component matched in the search query. Here is the greater context of the document found to be relevant during the search. This context is two levels up from the end of the component ID, whatever section/part/attachment etc. that may be:

    {section_context}

    Provide the user with an overview of the content within the section, with a focus on content related to the search query. The goal here is NOT to answer the user's query, but to explain what information the user can expect to find within this section of the document. Do not include a conclusion.
    """

    # Create a chat completion with streaming
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    # Collect the streamed response
    summary = ""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            summary += chunk.choices[0].delta.content

    return summary.strip()

# Function to display the sidebar content
def display_sidebar(result, query):    
    # Display the same information as col2 of the card
    location_code = result.metadata.get("Location", "")
    title = result.metadata.get("Title", "")
    type_ = result.metadata.get("Type", "")
    date = result.metadata.get("Date", "")
    component_id = result.metadata.get("ID", "")  # This is the component ID
    
    title_formatted = title.replace("-", " ").title()
    
    st.sidebar.header(f"{title_formatted}, {type_}, {date}")

    location = next(key for key, value in LOCATION_CODES.items() if value == location_code)

    st.sidebar.markdown(f"**{location}**")

    # Load the XML file for the selected document
    expression_title = f"_akn_{location_code}_act_{type_}_{date}_{title}_{result.metadata.get('Language', '')}@{result.metadata.get('Updated', '')}"
    file_name = f"{expression_title}.xml"
    file_path = os.path.join("expressions", file_name)

    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            xml_content = file.read()

        with st.spinner('Generating summaries...'):
            # Extract the preamble and section context using the component_id
            preamble = extract_preamble(xml_content)
            section_context = extract_section_context(xml_content, component_id)

            if preamble:
                # Generate a summary of the document using the preamble
                document_summary = generate_document_summary(query, title_formatted, location_code, date, preamble)
                st.sidebar.markdown("### Summary of Document")
                st.sidebar.markdown(document_summary)

            if section_context:
                # Generate a summary of the section using the section context and component ID
                section_summary = generate_section_summary(query, title_formatted, location_code, date, section_context, component_id)
                st.sidebar.markdown("### Summary of Section")
                st.sidebar.markdown(section_summary)
            else:
                st.sidebar.error("Unable to find the relevant section or context in the document.")
    else:
        st.sidebar.error("The requested document does not exist.")