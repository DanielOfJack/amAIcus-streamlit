import os
import streamlit as st
from lxml import etree

# Function to parse and render XML
def render_xml(xml_content):
    root = etree.fromstring(xml_content)
    formatted_xml = etree.tostring(root, pretty_print=True).decode()
    return formatted_xml

# Function to display the full XML file with Akoma Ntoso styling
def display_full_law(expression_title):
    
    file_name = f"{expression_title}.xml"
    file_path = os.path.join("expressions", file_name)
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            xml_content = file.read()
        
        formatted_xml = render_xml(xml_content)
        
        st.markdown(f"## {expression_title.replace('_', ' ').title()}")
        
        # Render the law using Akoma Ntoso style widgets, without the sidebar TOC
        st.markdown(
            f"""
            <div style="display: flex">
                <div style="flex: 1">
                    <la-decorate-terms popup-definitions link-terms></la-decorate-terms>
                    <la-decorate-internal-refs popups flag></la-decorate-internal-refs>
                    <la-akoma-ntoso>
                        {formatted_xml}
                    </la-akoma-ntoso>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <script type="module" src="https://cdn.jsdelivr.net/npm/@lawsafrica/law-widgets@latest/dist/lawwidgets/lawwidgets.esm.js"></script>
            """,
            unsafe_allow_html=True
        )
    else:
        st.error("The requested file does not exist.")