import pandas as pd
import numpy as np
import io
import streamlit as st # Belangrijk: Voeg deze import toe om st.write te kunnen gebruiken

def transformeer_percelen_bestand(input_source, output_target=None, vaste_id_kolommen=None, is_string_input=False):
    """
    Importeert een tab-gescheiden tekstbestand (of string) met percelen in kolommen
    en transformeert deze naar een tabel waarin de percelen onder elkaar staan.
    Alle verwachte basiskolommen blijven behouden, ook als ze leeg zijn.

    Args:
        input_source (str or io.StringIO): De naam van het invoer TXT-bestand
                                            OF de string-inhoud van het bestand.
        output_target (io.BytesIO or None): Een BytesIO-object voor in-memory output.
                                            Indien None, zal de functie een BytesIO-object retourneren.
        vaste_id_kolommen (list, optional): Een lijst met namen van kolommen
                                            die ongewijzigd moeten blijven (niet gepivoteerd)
                                            en geen perceelnummers bevatten.
                                            Bijv. ['ID_Project', 'Naam_Aanvrager'].
                                            Standaard is None.
        is_string_input (bool): Stel True in als input_source een string-inhoud is
                                 (voor web-applicaties), anders False (voor bestandsnaam).
    
    Returns:
        io.BytesIO or pd.DataFrame or None: Een BytesIO-object met de getransformeerde data
                                            als output_target None is, of een DataFrame
                                            als er geen percelen gevonden zijn, anders None bij fout.
    """

    # 1. Lees het tab-gescheiden TXT-bestand of de string inhoud
    if is_string_input:
        st.info("Lezen van de geüploade bestandinhoud...")
        try:
            df = pd.read_csv(io.StringIO(input_source), sep='\t', decimal='.') 
            st.success("Bestandinhoud succesvol ingelezen.")
        except Exception as e:
            st.error(f"Fout bij het lezen van de bestandinhoud: {e}")
            return None # Geef None terug bij fout voor string-input
    else: # Deze tak wordt niet gebruikt in de Streamlit app, maar is voor consistentie
        st.info(f"Lezen van het bestand: {input_source}...")
        try:
            df = pd.read_csv(input_source, sep='\t', decimal='.') 
            st.success("Bestand succesvol ingelezen.")
        except FileNotFoundError:
            st.error(f"Fout: Het bestand '{input_source}' is niet gevonden. Controleer de bestandsnaam en het pad.")
            return None
        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het lezen van het bestand: {e}")
            return None

    # Strippen van spaties uit alle kolomnamen direct na het inlezen
    df.columns = df.columns.str.strip()

    # Definieer de *verwachte* basiskolomnamen zonder de nummers
    expected_base_kolomnamen = [
        'E_Tab_Kad_Gem', 'E_SectieLtr', 'E_SectieNr', 'E_Tab_Opp', 'E_Tab_NN',
        'E_Tab_Subs_Onderd', 'E_Tab_Rijks_Prov_NNB', 'E_Tab_Rijks_Inv_Opt',
        'E_Tab_Prov_Inv_Opt', 'E_Tab_PAS_Ben_Perc', 'E_Tab_Inv_ONNB',
        'E_Tab_Inv_Versn_N2000', 'E_Tab_Vgst_InTeRi_AT', 'E_Tab_Afw_Tov_AK_Zkgb'
    ]
    
    # Lijst van basiskolomnamen die numeriek moeten zijn
    numeric_base_columns = ['E_Tab_Opp', 'E_Tab_NN'] 

    # 2. Bepaal het maximale perceelnummer uit de kolomnamen
    max_perceel_nummer = 0
    for col in df.columns:
        parts = col.rsplit('_', 1) 
        if len(parts) > 1 and parts[-1].isdigit():
            num = int(parts[-1])
            if num > max_perceel_nummer:
                max_perceel_nummer = num

    if max_perceel_nummer == 0:
        st.warning("Geen genummerde perceelkolommen gevonden in het bestand. Controleer de kolomnamen. Er wordt geprobeerd door te gaan met alleen vaste ID-kolommen.")
        if vaste_id_kolommen and all(col in df.columns for col in vaste_id_kolommen):
            # Als er geen percelen zijn, maar wel vaste ID-kolommen, geef die dan terug
            df_output = df[vaste_id_kolommen].copy()
            output_buffer_no_perceel = io.BytesIO()
            df_output.to_csv(output_buffer_no_perceel, sep=';', index=False, decimal=',')
            output_buffer_no_perceel.seek(0)
            return output_buffer_no_perceel
        else:
            st.error("Geen zinvolle output mogelijk, geen percelen of vaste ID-kolommen gevonden.")
            return pd.DataFrame() # Retourneer een lege DataFrame voor Streamlit

    # 3. Bouw de lijst met kolommen die 'gemolten' moeten worden
    kolommen_om_te_smelten = []
    for i in range(1, max_perceel_nummer + 1):
        for base_col in expected_base_kolomnamen: 
            full_col_name = f"{base_col}_{i}"
            if full_col_name in df.columns:
                kolommen_om_te_smelten.append(full_col_name)

    kolommen_om_te_smelten = [col for col in kolommen_om_te_smelten if not col.startswith('E_Tab_Plus_')]


    # 4. Bepaal de 'id_vars' (kolommen die niet gepivoteerd moeten worden)
    actual_id_vars = []
    if vaste_id_kolommen:
        for col in vaste_id_kolommen:
            stripped_col = col.strip()
            if stripped_col in df.columns:
                actual_id_vars.append(stripped_col)
            else:
                st.warning(f"Waarschuwing: Vaste ID-kolom '{stripped_col}' niet gevonden in het bestand en wordt overgeslagen.")

    df['unieke_rij_id'] = df.index
    actual_id_vars.append('unieke_rij_id')

    relevant_cols_for_melt = list(set(kolommen_om_te_smelten + actual_id_vars))
    df_filtered = df[relevant_cols_for_melt].copy()
    
    st.info("Transformeren van de gegevens (melten/unpivoting)...")
    if not kolommen_om_te_smelten:
        st.warning("Geen kolommen gevonden om te smelten. Controleer de kolomnamen en het patroon.")
        if actual_id_vars:
            df_output = df[actual_id_vars].copy()
            output_buffer_no_perceel = io.BytesIO()
            df_output.to_csv(output_buffer_no_perceel, sep=';', index=False, decimal=',')
            output_buffer_no_perceel.seek(0)
            return output_buffer_no_perceel
        else:
            st.error("Geen zinvolle output mogelijk.")
            return pd.DataFrame()

    df_gemolten = pd.melt(df_filtered, 
                          id_vars=actual_id_vars, 
                          value_vars=kolommen_om_te_smelten, 
                          var_name='Oorspronkelijke_Kolom', 
                          value_name='Waarde')
    
    # --- START DIAGNOSTISCHE REGELS ---
    #st.write("--- Diagnostische Output (df_gemolten na melt) ---")
    #st.write("Kolommen in df_gemolten vóór splitsing:", df_gemolten.columns.tolist())
    
    #df_gemolten[['Basisnaam', 'PerceelNummer']] = df_gemolten['Oorspronkelijke_Kolom'].str.rsplit('_', n=1, expand=True)
    
    #st.write("Kolommen in df_gemolten ná splitsing:", df_gemolten.columns.tolist())
    #st.write("Unieke waarden in 'Basisnaam' kolom:", df_gemolten['Basisnaam'].unique().tolist())

    #pivot_index_cols = actual_id_vars.copy()
    #if 'PerceelNummer' in df_gemolten.columns:
    #    pivot_index_cols.append('PerceelNummer')
    
    #st.write("pivot_index_cols (index voor pivot):", pivot_index_cols)
    #st.write("expected_base_kolomnamen (kolommen voor pivot):", expected_base_kolomnamen)
    #st.write("--- Einde Diagnostische Output ---")
    # --- EINDE DIAGNOSTISCHE REGELS ---

    # 6. Pivoteren om de gewenste kolomstructuur te krijgen
    df_getransformeerd = df_gemolten.pivot_table(index=pivot_index_cols,
                                                 columns='Basisnaam', # Gebruik direct de 'Basisnaam' kolom
                                                 values='Waarde', 
                                                 aggfunc='first')

    df_getransformeerd = df_getransformeerd.reset_index()

    # Verwijder de naam van de kolommen-as (die 'Basisnaam' zal zijn na reset_index)
    df_getransformeerd.columns.name = None 

    # --- Zorg dat alle verwachte basiskolommen bestaan en in de juiste volgorde staan ---
    # Voeg ontbrekende kolommen toe met NaN voordat we de uiteindelijke selectie en volgorde bepalen
    for col_name in expected_base_kolomnamen:
        if col_name not in df_getransformeerd.columns:
            df_getransformeerd[col_name] = np.nan # Voeg de kolom toe als deze ontbreekt

    # --- CONVERTEER NUMERIEKE KOLOMMEN EN BEHANDEL NAN ---
    st.info("Converteren van numerieke kolommen en behandelen van lege waarden...")
    for col_name in numeric_base_columns:
        if col_name in df_getransformeerd.columns:
            df_getransformeerd[col_name] = pd.to_numeric(df_getransformeerd[col_name], errors='coerce')
            # Optioneel: Vervang NaN door een lege string om Excel-interpretatie te verbeteren
            # df_getransformeerd[col_name] = df_getransformeerd[col_name].fillna('') 

    # 7. Verwijder de tijdelijke 'unieke_rij_id'
    kolommen_om_te_droppen = ['unieke_rij_id'] 
    df_getransformeerd = df_getransformeerd.drop(columns=kolommen_om_te_droppen, errors='ignore')
    
    # 8. Hernoem en herschik de kolommen voor de uiteindelijke output
    desired_final_output_cols = []
    if vaste_id_kolommen:
        for col in vaste_id_kolommen:
            stripped_col = col.strip()
            if stripped_col in df_getransformeerd.columns:
                desired_final_output_cols.append(stripped_col)
    
    # Voeg PerceelNummer toe als het bestaat en nog niet is toegevoegd (logische plek na vaste ID's)
    if 'PerceelNummer' in df_getransformeerd.columns and 'PerceelNummer' not in desired_final_output_cols:
        if vaste_id_kolommen:
            desired_final_output_cols.insert(len(vaste_id_kolommen), 'PerceelNummer')
        else:
            desired_final_output_cols.insert(0, 'PerceelNummer')
            
    # Voeg NU alle expected_base_kolomnamen toe, in de gedefinieerde volgorde.
    for base_col in expected_base_kolomnamen:
        if base_col not in desired_final_output_cols: # Voorkom duplicaten
            desired_final_output_cols.append(base_col)

    # Dit is BELANGRIJK: Voeg ontbrekende kolommen toe met NaN voordat we selecteren om fouten te voorkomen
    # Deze stap is nu dubbel gecheckt en correct geplaatst voor de uiteindelijke selectie
    for col in desired_final_output_cols:
        if col not in df_getransformeerd.columns:
            df_getransformeerd[col] = np.nan 
            
    df_getransformeerd = df_getransformeerd[desired_final_output_cols] # Gebruik de complete lijst
    
    st.success("Transformatie voltooid.")
    
    # 9. Sla de getransformeerde DataFrame op naar een in-memory buffer
    # De output_target parameter wordt nu gebruikt
    if output_target is None:
        output_buffer = io.BytesIO()
    else:
        output_buffer = output_target
        
    df_getransformeerd.to_excel(output_buffer, index=False, engine='xlsxwriter')
    output_buffer.seek(0) # Belangrijk: zet de cursor terug naar het begin van de buffer
    return output_buffer