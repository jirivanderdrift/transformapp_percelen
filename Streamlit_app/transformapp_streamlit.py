import streamlit as st
import pandas as pd
import os # Nodig voor path.splitext
import io # Nodig voor StringIO en BytesIO

# Importeer de transformatiefunctie uit het aparte bestand
# Zorg ervoor dat percelen_transformatie_logica.py in dezelfde map staat
from percelen_transformatie_logica import transformeer_percelen_bestand

st.set_page_config(layout="wide")

st.title('Bestandstransformator voor Percelen')
st.write("Upload een tab-gescheiden TXT-bestand met perceelgegevens in genummerde kolommen. De tool transformeert deze naar een lange tabel waarin elk perceel een eigen rij krijgt.")

uploaded_file = st.file_uploader("Kies een TXT-bestand", type="txt")

# Optionele invoer voor vaste ID-kolommen
st.sidebar.header("Optionele instellingen")
vaste_id_kolommen_input = st.sidebar.text_area(
    "Voer vaste ID-kolommen in (scheiden met komma, bijv. ID_Project, Naam_Aanvrager)",
    value=""
)
vaste_id_cols = [col.strip() for col in vaste_id_kolommen_input.split(',') if col.strip()] if vaste_id_kolommen_input else None

if uploaded_file is not None:
    st.info("Bestand succesvol geüpload! Start transformatie...")

    try:
        # Lees de inhoud van het geüploade bestand
        file_content = uploaded_file.getvalue().decode("utf-8")

        # Bepaal de output bestandsnaam
        base_filename = os.path.splitext(uploaded_file.name)[0]
        output_filename = f"{base_filename}_percelen.xlsx" # Dit is nu alleen de naam, niet het pad

        # Roep de transformatiefunctie aan
        # We geven True mee voor is_string_input omdat we de inhoud van het bestand als string doorgeven
        # De output_target is nu een BytesIO-object, niet een bestandsnaam
        output_buffer = transformeer_percelen_bestand(
            input_source=file_content,
            output_target=io.BytesIO(), 
            vaste_id_kolommen=vaste_id_cols,
            is_string_input=True
        )

        # De volgende blokken moeten correct geïndenteerd zijn,
        # op hetzelfde niveau als 'output_buffer = transformeer_percelen_bestand(...)'.
        # Dit was de fout!
        if output_buffer:
            st.success("Transformatie voltooid!")
            
            output_buffer.seek(0) # Zorg ervoor dat de buffer gereset is

            st.download_button(
                label="Download Getransformeerd Excel", 
                data=output_buffer,
                file_name=output_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            )
            
            # ALS JE WEL EEN PREVIEW WILT VAN DE EXCEL OUTPUT:
            try:
                # Reset buffer voor het lezen
                output_buffer.seek(0) 
                output_df_display = pd.read_excel(output_buffer)
                st.subheader("Voorbeeld van getransformeerde data:")
                st.dataframe(output_df_display.head())
                output_buffer.seek(0) # Reset buffer na tonen, essentieel voor de downloadknop
            except Exception as e:
                st.warning(f"Kon geen preview van Excel-bestand tonen: {e}")

        else: # Deze else hoort bij de if output_buffer:
            st.error("Transformatie mislukt. Controleer de invoergegevens en kolomstructuur.")

    except Exception as e: # Deze except hoort bij de try bovenin (na `if uploaded_file is not None:`)
        st.error(f"Er is een onverwachte fout opgetreden: {e}. Zorg ervoor dat het bestand correct geformatteerd is.")
        st.exception(e) # Toon de volledige traceback voor debugging