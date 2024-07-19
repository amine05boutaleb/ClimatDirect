import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import urllib.parse
import ast
from datetime import datetime
import pandas as pd
from datetime import timedelta
import plotly.express as px
import time
import io
st.set_page_config(page_title="ClimatDirect",page_icon="https://i.etsystatic.com/23821301/r/il/dcbcfc/2484217158/il_570xN.2484217158_oi4q.jpg",layout="wide")
data_station = [{'oaci': item['fields']['oaci'], 'titre': item['fields']['titre']} for item in ast.literal_eval(requests.get("https://map.aerobreak.com/data/dt.js").content.decode('utf-8')[:-1].split("=")[1])]


def get_adresse(longitude, latitude):
    api_url = "https://api.opencagedata.com/geocode/v1/json?q="+str(latitude)+"+"+str(longitude)+"&key=a1674daf25f54056a7c8047ca1742c22&no_annotations=1&language=fr"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    data = response.json()
    try:
        city = data['results'][0]['components']['city']
    except:
        city = data['results'][0]['components']['_normalized_city']
    texte_encode = urllib.parse.quote(f"{city+ ', '+data['results'][0]['components']['county']+ ', '+ data['results'][0]['components']['country']}")
    return data["results"][0]["formatted"], texte_encode
def trouver_titre_par_oaci(liste, code_oaci):
    for aerodrome in liste:
        if aerodrome['oaci'] == code_oaci:
            return aerodrome['titre']
    return None  
def get_station (adresse_encoded):
    api_url = f"https://api.weather.com/v3/location/search?apiKey=e1f10a1e78da46f5b10a1e78da96f525&language=en-US&query={adresse_encoded}&locationType=city%2Cairport%2CpostCode%2Cpws&format=json"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'} # This is chrome, you can set whatever browser you like
    try:
        with requests.Session() as session:
            response = session.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data['location']["icaoCode"][0]
    except requests.exceptions.RequestException as e:
        return(f"Erreur lors de la requête : {e}")
def get_temp(station, date):
    api_url = f"https://api.weather.com/v1/location/{station}:9:FR/observations/historical.json?apiKey=e1f10a1e78da46f5b10a1e78da96f525&units=e&startDate={date}"
    try:
        with requests.Session() as session:
            response = session.get(api_url)
            response.raise_for_status()
            data = response.json()["observations"]
        return data
    except requests.exceptions.RequestException as e:
        return(f"Erreur lors de la requête : {e}")
def get_data_final(liste_dates, texte_encode, frequence, temperature, humidity, vent, pression, precip, dew_point, d_debut, d_fin):
    print(liste_dates)
    external_data = {"Date": [],"Pression (in)": [],"Humidité (%)": [],"Vitesse du vent (mph)": [],"Température (°F)": [], "Point de rosée (°F)":[], "Précipitation (in)":[]}
    progress_bar = st.progress(0)
    for index, date in enumerate(liste_dates):
        percentage = (index + 1) / len(liste_dates)
        progress_bar.progress(percentage)
        annee = date.year
        mois = f"{date.month:02}" 
        jour = f"{date.day:02}"
        resultsss = f"{annee}{mois}{jour}"
        data_journee = get_temp(get_station(texte_encode), resultsss)
        if frequence=="1 mesure / demi-heure":
            for data_heure in data_journee:
                external_data["Date"].append(datetime.utcfromtimestamp(data_heure["valid_time_gmt"]))
                external_data["Pression (in)"].append(data_heure["pressure"])
                external_data["Humidité (%)"].append(data_heure["rh"])
                external_data["Vitesse du vent (mph)"].append(data_heure["wspd"])
                external_data["Température (°F)"].append(data_heure["temp"])
                external_data["Point de rosée (°F)"].append(data_heure["dewPt"])
                external_data["Précipitation (in)"].append(data_heure["uv_index"])
        elif frequence=="1 mesure / heure":
            for data_heure in data_journee:
                if datetime.utcfromtimestamp(data_heure["valid_time_gmt"]).minute==0:
                    external_data["Date"].append(datetime.utcfromtimestamp(data_heure["valid_time_gmt"]))
                    external_data["Pression (in)"].append(data_heure["pressure"])
                    external_data["Humidité (%)"].append(data_heure["rh"])
                    external_data["Vitesse du vent (mph)"].append(data_heure["wspd"])
                    external_data["Température (°F)"].append(data_heure["temp"])
                    external_data["Point de rosée (°F)"].append(data_heure["dewPt"])
                    external_data["Précipitation (in)"].append(data_heure["uv_index"])
    external_data = pd.DataFrame(external_data)
    external_data = external_data[(external_data["Date"].dt.date>=d_debut)&(external_data["Date"].dt.date<=d_fin)]
    if not temperature:
        external_data = external_data.drop(columns="Température (°F)")
    if not humidity:
        external_data = external_data.drop(columns="Humidité (%)")
    if not vent:
        external_data = external_data.drop(columns="Vitesse du vent (mph)")
    if not pression:
        external_data = external_data.drop(columns="Pression (in)")
    if not precip:
        external_data = external_data.drop(columns="Précipitation (in)")
    if not dew_point:
        external_data = external_data.drop(columns="Point de rosée (°F)")
    return external_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')
def convert_df_to_xlsx(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Feuille1')
    return output.getvalue()
st.title("ClimatDirect")
st.header("Données climatiques gratuites par coordonnées et date")
st.markdown(f"ClimatDirect est une application web gratuite qui fournit des données climatiques détaillées pour des endroits en France <img src='https://www.reliflex.in/assets/img/partners/france-flag.png' height='15'> , incluant la température, l'humidité, la vitesse du vent et bien plus encore, basées sur des coordonnées spécifiques et une date donnée. Accédez facilement à des informations météorologiques précises pour n'importe quel lieu en France et moment.", unsafe_allow_html=True)
st.markdown("""<style>.warning {background-color: #ffcc00;color: #660000;padding: 3px;border-radius: 5px;}</style>""", unsafe_allow_html=True)

st.write("")
colA, col_space, colB = st.columns([1, 0.1, 1])

with colA:
    col1, col2 = st.columns(2)
    with col1:
        longitude = st.number_input('Entrez la longitude', format="%.10f", value=6.100165)
    with col2:
        latitude = st.number_input('Entrez la latitude', format="%.10f", value=43.126223)
    m = folium.Map(location=[latitude, longitude], zoom_start=5)
    folium.Marker([latitude, longitude], tooltip='Location').add_to(m)
    st_folium(m, width="100%", height=500)
with colB:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Adresse :")
        st.write(get_adresse(longitude, latitude)[0])
    with col2:
        st.subheader("Station météo concernée :")
        texte_encode = get_adresse(longitude, latitude)[1]
        st.write(trouver_titre_par_oaci(data_station, get_station(texte_encode)))
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Date début :")
        d_debut = st.date_input("Date début des données",datetime.now()-timedelta(days=1), max_value=datetime.now()-timedelta(days=1))
    with col2:
        st.subheader("Date fin :")
        d_fin = st.date_input("Date fin des données",datetime.now()-timedelta(days=1), max_value=datetime.now()-timedelta(days=1))
    st.subheader("Les données à extraire :")
    col1, col2 = st.columns(2)
    with col1:
        temperature = st.toggle("Température", value=True)
        humidity = st.toggle("Humidité", value=True)
        vent = st.toggle("Vitesse du vent", value=True)
    with col2:
        pression = st.toggle("Pression", value=True)
        precip = st.toggle("Précipitation", value=True)
        dew_point = st.toggle("Point de Rosée", value=True)
    st.subheader("Fréquence des données :")
    frequence = st.radio("Fréquence des données", ["1 mesure / heure", "1 mesure / demi-heure"])
    if st.button("Générer le fichier"):
        if d_debut>d_fin:
            st.warning('La date fin doit être après la date début', icon="⚠️")
        else:
            liste_dates = []
            date_actuelle = d_debut
            while date_actuelle <= d_fin+pd.Timedelta(days=1):
                liste_dates.append(date_actuelle)
                date_actuelle += pd.Timedelta(days=1)
            external_data = get_data_final(liste_dates, texte_encode, frequence, temperature, humidity, vent, pression, precip, dew_point, d_debut, d_fin)

try:
    st.dataframe(external_data, use_container_width=True)
    variable = len(external_data.columns)-1
    rows = (variable + 2) // 3
    cols = variable if variable <= 3 else 3
    index = 1
    for row in range(rows):
        cols_in_row = min(cols, variable - row * cols)
        cols_placeholder = st.columns(cols_in_row)
        for col in range(cols_in_row):
            with cols_placeholder[col]:
                fig = px.line(external_data, x="Date", y=external_data.columns[index], markers=True)
                fig.update_traces(marker=dict(size=3, color='green'),line=dict(width=1, color='blue'))
                st.plotly_chart(fig, use_container_width=True)
                index+=1
    csv = convert_df_to_csv(external_data)
    st.download_button(label="Télécharger en CSV",data=csv,file_name='données climatiques.csv',mime='text/csv')
    xlsx = convert_df_to_xlsx(external_data)
    st.download_button(label="Télécharger en XLSX",data=xlsx,file_name='données climatiques.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
except:
    pass




