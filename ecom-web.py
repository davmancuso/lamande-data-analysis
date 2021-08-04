import locale
import json
import requests
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import statsmodels.api as sm

# ------------------------------
#             STYLE
# ------------------------------
st.markdown("""
    <style type='text/css'>

        /* ...styles... */
    
    </style>
""", unsafe_allow_html=True)

# ------------------------------
#             LINGUA
# ------------------------------
locale.setlocale(locale.LC_ALL , 'it_IT')

it_IT_format = {
    "decimal": ",",
    "thousands": ".",
    "grouping": [3],
    "currency": ["€", ""],
    "dateTime": "%a, %e %b %Y - %X",
    "date": "%d/%m/%Y",
    "time": "%H:%M:%S",
    "periods": ["AM", "PM"],
    "days": ["Domenica", "Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato"],
    "shortDays": ["Dom", "Lun", "Mar", "Mer", "Gio", "Ven", "Sab"],
    "months": ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"],
    "shortMonths": ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
}

# Non funziona con Streamlit...
# alt.renderers.set_embed_options(timeFormatLocale=it_IT_format)

# ------------------------------
#           FUNCTIONS
# ------------------------------
def url_retrieving(source, start_date, end_date, status):
    start_date_url = str(start_date.strftime("%Y%m%d"))
    end_date_url = str(end_date.strftime("%Y%m%d"))

    url = source+'?from='+start_date_url+'&to='+end_date_url+'&status='+status
    resp = requests.get(url)

    return resp.json()

def data_cleaning(df):
    df['OrderID'] = df['OrderID'].astype(int)
    df['cOrderDate'] = [odate.date() for odate in pd.to_datetime(df['OrderDate'])]
    df['cOrderTime'] = [otime.time() for otime in pd.to_datetime(df['OrderDate'])]
    df['OrderSubTotal'] = df['OrderSubTotal'].astype(float)
    df['TotalDiscount'] = df['TotalDiscount'].astype(float)
    df['OrderTotal'] = df['OrderTotal'].astype(float)
    df['AnnoNascita'] = df['AnnoNascita'].astype(int, errors='ignore')
    df['Age'] = df['Age'].astype(int, errors='ignore')

    del df['Email']
    del df['OrderDate']
    
    df.replace("-", np.nan, inplace=True)
    
    df = df[[
        'OrderID',
        'cOrderDate',
        'cOrderTime',
        'OrderStatus',
        'OrderSubTotal',
        'Coupon',
        'TotalDiscount',
        'OrderTotal',
        'Gender',
        'AnnoNascita',
        'Age',
        'Provincia',
        'OrderItems'
    ]]

    return df

def daily_order(df):
    daily_totals = df.groupby(['cOrderDate']).sum()

    plt.figure(figsize=(8,4), dpi=80)
    plt.plot(daily_totals.index, daily_totals['OrderTotal'], color='black', marker='o')
    plt.title('Fatturato giornaliero')
    plt.xlabel('')
    plt.xticks(rotation=45)
    plt.ylabel('Fatturato (in Euro)')
    plt.grid(True)
    plt.tight_layout()
    st.pyplot(plt)

    # chart_data = pd.DataFrame({
    #     'Data': daily_totals.index,
    #     'Totale': daily_totals['OrderTotal']
    # })
    
    # st.altair_chart(
    #     alt.Chart(chart_data, title="Fatturato giornaliero")
    #         .mark_line(point=True)
    #         .encode(
    #             alt.X('Data', title='Data'),
    #             alt.Y('Totale', title='Totale (in Euro)'),
    #             tooltip=[
    #                 alt.Tooltip('Totale', title="Fatturato", format=",.5r")
    #             ],
    #         ), use_container_width=True
    # )

def spending_ranges(df):
    prices_bins = [0.00, 25.00, 50.00, 75.00, 100.00, 50000.00]
    prices_class = [
        "Fino a € 24,99",
        "Da € 25,00 a € 49,99",
        "Da € 50,00 a € 74,99",
        "Da € 75,00 a € 99,99",
        "Oltre € 100,00"
    ]

    price_order_total = pd.cut(df['OrderTotal'].astype(float), bins=prices_bins, labels=prices_class).value_counts()
    price_order_label = [
        price_order_total.index[i] for i in range(len(price_order_total))
    ]

    plt.figure(figsize=(8,4), dpi=80)
    plt.axis('equal')
    plt.pie(x=price_order_total, autopct='%1.2f%%', shadow=False)
    plt.title('Intervalli di spesa per singolo ordine')
    plt.ylabel('')
    plt.legend(labels=price_order_label, loc="upper right")
    plt.tight_layout()
    st.pyplot(plt)

    return

def spent_per_age(df):
    age_bins = [0, 18, 25, 35, 45, 55, 65, 200]
    age_class = [
        "Fino a 17 anni",
        "Da 18 a 24 anni",
        "Da 25 a 34 anni",
        "Da 35 a 44 anni",
        "Da 45 a 54 anni",
        "Da 55 a 64 anni",
        "Oltre i 65 anni"
    ]

    age_order_total = pd.cut(df['OrderTotal'].astype(float), bins=age_bins, labels=age_class).value_counts(dropna=True)
    age_order_label = [
        age_order_total.index[i] for i in range(len(age_order_total))
    ]

    plt.figure(figsize=(8,4), dpi=80)
    plt.axis('equal')
    plt.pie(x=age_order_total, autopct='%1.2f%%', shadow=False)
    plt.title('Range di spesa per età')
    plt.ylabel('')
    plt.legend(labels=age_order_label, loc="upper right")
    plt.tight_layout()
    st.pyplot(plt)

    return

def core_analysis(source, start_date, end_date, status, status_str):
    if start_date > end_date:
        st.error('Errore: La data di fine deve essere successiva alla data di inizio')
        return
    
    with st.spinner("Recupero degli ordini in corso..."):
        txt = url_retrieving(source, start_date, end_date, status)
    
    if not txt:
        st.error("Nessun ordine trovato.")
        return
    
    with st.spinner("Pulizia del database degli ordini..."):
        df_raw = pd.DataFrame(txt['Orders'])
        df = data_cleaning(df_raw)

    st.header("Anteprima generale")
    if status == "":
        status = "Tutti"
    st.success("Ordini dal `%s` al `%s`\n\nStato degli ordini: `%s`" % (start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y"), status_str))

    st.subheader("Dataset")
    st.write(df)

    st.header("Analisi degli ordini")
    with st.spinner("Tracciamento del grafico \"Fatturato giornaliero\"..."):
        daily_order(df)
    
    with st.spinner("Tracciamento del grafico \"Intervalli di spesa per singolo ordine\"..."):
        spending_ranges(df)
    
    with st.spinner("Tracciamento del grafico \"Range di spesa per età\"..."):
        spent_per_age(df)

    return

# ------------------------------
#             SIDEBAR
# ------------------------------
st.sidebar.title("Analisi dei dati")
st.sidebar.subheader("Dati cliente")
st.sidebar.text("Cliente: L'Amande\nFonte dei dati: https://lamande.it/\nTipologia: Piattaforma WooCommerce")
st.sidebar.subheader("Dati agente")
st.sidebar.text("Data analyst: Davide Mancuso\nMail: d.mancuso@brainonstrategy.com\nTelefono: +39 392 035 9839")
st.sidebar.subheader("Dati agenzia")
st.sidebar.text("Agenzia: Brain on strategy srl\nWebsite: https://brainonstrategy.com/\nMail: info@brainonstrategy.com")

# ------------------------------
#             BODY
# ------------------------------
st.title("Parametri della analisi")

st.subheader("Inserire la fonte")
source = st.text_input("Fonte")

st.subheader("Selezionare il periodo desiderato")
start_date = st.date_input("Inizio", (datetime.today() - timedelta(days=365)))
end_date = st.date_input("Fine", datetime.today())

st.subheader("Selezionare lo stato degli ordini")
display_status = ("Tutti", "Eseguiti", "Cancellati")
num_status = list(range(len(display_status)))
status = st.radio("Stato", num_status, format_func = lambda x : display_status[x])

status_str = display_status[status]
if status == 0:
    status = ""
elif status == 1:
    status = "processing"
elif status == 2:
    status = "canceled"

if st.button("Scarica i dati"):
    core_analysis(source, start_date, end_date, status, status_str)
