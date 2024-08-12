import os
import streamlit as st
from lxml import etree
from openai import OpenAI

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

# Function to generate a summary using OpenAI
def generate_summary(query, search_content, section_context):
    client = OpenAI()

    prompt = f"""
    You are a legal assistant, helping a client to understand whether or not a legal document is relevant for what they are searching for. The client has asked:

    {query}

    The following is the search result found:

    {search_content}

    The following is the text-content of the full section of the legal document in which that response was found:

    {section_context}

    Please provide the client with a summary of the content of this section of the legal document, focusing strongly on any information that might be relevant. The goal is to help the client understand if this section of this document actually contains the information they want.
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
    st.sidebar.header("Additional Information")
    
    # Display the same information as col2 of the card
    location_code = result.metadata.get("Location", "")
    title = result.metadata.get("Title", "")
    type_ = result.metadata.get("Type", "")
    date = result.metadata.get("Date", "")
    doc_id = result.metadata.get("ID", "")
    
    title_formatted = title.replace("-", " ").title()

    st.sidebar.markdown(f"**{location_code}**")
    st.sidebar.markdown(f"### {title_formatted}, {type_}, {date}")
    st.sidebar.markdown(f"*{doc_id}*")

    # Load the XML file for the selected document
    expression_title = f"_akn_{location_code}_act_{type_}_{date}_{title}_{result.metadata.get('Language', '')}@{result.metadata.get('Updated', '')}"
    file_name = f"{expression_title}.xml"
    file_path = os.path.join("expressions", file_name)

    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            xml_content = file.read()

        # Extract the section context using the doc_id
        section_context = extract_section_context(xml_content, doc_id)

        if section_context:
            # Generate a summary using the query, search content, and section context
            summary = generate_summary(query, result.page_content.strip(), section_context)
            
            # Display the summary in the sidebar
            st.sidebar.markdown("### Summary of Section")
            st.sidebar.markdown(summary)
        else:
            st.sidebar.error("Unable to find the relevant section or context in the document.")
    else:
        st.sidebar.error("The requested document does not exist.")