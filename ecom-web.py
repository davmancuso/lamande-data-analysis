import environ
import json
import requests
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from datetime import datetime, timedelta
# from facebookads.adobjects.adspixel import AdsPixel

# ------------------------------
#             STYLE
# ------------------------------
st.markdown("""
    <style type='text/css'>

        /* Remove sidebar X button */
        [data-testid="stSidebar"] div div button {
            display: none;
        }

        /* Remove footer */
        footer {
            display: none !important;
        }
    
    </style>
""", unsafe_allow_html=True)

# ------------------------------
#           FUNCTIONS
# ------------------------------

# ---------- PIXEL ----------
# @st.cache
# def pixel_url_data(pixel_id, start_date, end_date):
#     pixel = AdsPixel(pixel_id)
#     dataset = pixel.get_stats(params={
#         'aggregation': 'custom_data_field',
#         'start_time': start_date,
#         'end_time': end_date,
#     })

#     st.write(dataset)

#     return dataset

# ---------- WOOCOMMERCE ----------
@st.cache
def url_retrieving(source, start_date, end_date, status):
    start_date_url = str(start_date.strftime("%Y%m%d"))
    end_date_url = str(end_date.strftime("%Y%m%d"))

    url = source+'?from='+start_date_url+'&to='+end_date_url+'&status='+status
    resp = requests.get(url)

    return resp.json()

@st.cache
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

def orders_retrieving(df):
    return df.drop(columns=['OrderItems'])

def products_retrieving(df):
    items = pd.json_normalize(df['OrderItems']).join(
        df[['OrderID', 'cOrderDate', 'OrderStatus']], how='left'
    ).explode(
        'Item'
    ).reset_index(
        drop=True
    )

    products = pd.json_normalize(items['Item']).join(
        items[['OrderID', 'cOrderDate', 'OrderStatus']], how='left'
    )

    products['Quantity'] = products['Quantity'].astype(float)
    products['ItemCost'] = products['ItemCost'].astype(float)
    products['ItemTotal'] = products['ItemTotal'].astype(float)
    products['Category'] = products['Category'].str.title()

    return products

def daily_order(df):
    daily_totals = df.groupby(['cOrderDate']).sum()

    chart_data = pd.DataFrame({
        'Data': daily_totals.index,
        'Totale': daily_totals['OrderTotal']
    })
    
    st.subheader("Fatturato giornaliero")
    st.altair_chart(
        alt.Chart(
            chart_data
        )
        .mark_line(
            point=True
        )
        .encode(
            alt.X('Data', title='Data'),
            alt.Y('Totale', title='Totale (in Euro)'),
            tooltip=[
                alt.Tooltip('Data', title="Giorno", format="%d/%m/%Y"),
                alt.Tooltip('Totale', title="Fatturato (in Euro)")
            ],
        )
        .interactive()
        .configure_point(
            size=100
        ), use_container_width=True
    )

def spending_ranges(df):
    prices_bins = [0.00, 25.00, 50.00, 75.00, 100.00, 50000.00]
    prices_class = [
        "Fino a € 24,99",
        "Da € 25,00 a € 49,99",
        "Da € 50,00 a € 74,99",
        "Da € 75,00 a € 99,99",
        "Oltre € 100,00"
    ]

    orders = [
        len(df.loc[
            (df['OrderTotal'] >= prices_bins[i - 1])
            & (df['OrderTotal'] < prices_bins[i])
        ])
        for i in range(1, len(prices_class)+1)
    ]

    totals = [
        df.loc[
            (df['OrderTotal'] >= prices_bins[i - 1])
            & (df['OrderTotal'] < prices_bins[i])
        ]['OrderTotal'].sum()
        for i in range(1, len(prices_class)+1)
    ]

    chart_data = pd.DataFrame({
        'Fascia': prices_class,
        'Ordini': orders,
        'Totale': totals
    })
    
    st.header("Analisi per fasce di prezzo")
    st.subheader("Numero di ordini")
    st.altair_chart(
        alt.Chart(
            chart_data,
            title="Intervalli di prezzo per ordine"
        )
        .mark_bar()
        .encode(
            alt.X('Fascia', title='Fascia di prezzo', sort=prices_class),
            alt.Y('Ordini', title='Ordini'),
            tooltip=[
                alt.Tooltip('Fascia', title="Fascia"),
                alt.Tooltip('Ordini', title="Ordini"),
                alt.Tooltip('Totale', title="Fatturato (in Euro)")
            ],
        )
        .configure_axisX(
            labelAngle=0
        ), use_container_width=True
    )

    st.subheader("Fatturato totale")
    st.altair_chart(
        alt.Chart(
            chart_data,
            title="Intervalli di prezzo per fatturato"
        )
        .mark_bar()
        .encode(
            alt.X('Fascia', title='Fascia di prezzo', sort=prices_class),
            alt.Y('Totale', title='Totale (in Euro)'),
            tooltip=[
                alt.Tooltip('Fascia', title="Fascia"),
                alt.Tooltip('Totale', title="Totale (in Euro)"),
                alt.Tooltip('Totale', title="Fatturato (in Euro)")
            ],
        )
        .configure_axisX(
            labelAngle=0
        ), use_container_width=True
    )

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

    orders = [
        len(df.loc[
            (df['OrderTotal'] >= age_bins[i - 1])
            & (df['OrderTotal'] < age_bins[i])
        ])
        for i in range(1, len(age_class)+1)
    ]

    totals = [
        df.loc[
            (df['OrderTotal'] >= age_bins[i - 1])
            & (df['OrderTotal'] < age_bins[i])
        ]['OrderTotal'].sum()
        for i in range(1, len(age_class)+1)
    ]

    chart_data = pd.DataFrame({
        'Fascia': age_class,
        'Ordini': orders,
        'Totale': totals
    })
    
    st.header("Analisi per fasce di età")
    st.subheader("Numero di ordini")
    st.altair_chart(
        alt.Chart(
            chart_data,
            title="Intervalli di età per ordine"
        )
        .mark_bar()
        .encode(
            alt.X('Fascia', title='Fascia di età', sort=age_class),
            alt.Y('Ordini', title='Ordini'),
            tooltip=[
                alt.Tooltip('Fascia', title="Fascia"),
                alt.Tooltip('Ordini', title="Ordini"),
                alt.Tooltip('Totale', title="Fatturato (in Euro)")
            ],
        )
        .configure_axisX(
            labelAngle=0
        ), use_container_width=True
    )

    st.subheader("Fatturato totale")
    st.altair_chart(
        alt.Chart(
            chart_data,
            title="Intervalli di età per fatturato"
        )
        .mark_bar()
        .encode(
            alt.X('Fascia', title='Fascia di età', sort=age_class),
            alt.Y('Totale', title='Totale (in Euro)'),
            tooltip=[
                alt.Tooltip('Fascia', title="Fascia"),
                alt.Tooltip('Ordini', title="Ordini"),
                alt.Tooltip('Totale', title="Fatturato (in Euro)")
            ],
        )
        .configure_axisX(
            labelAngle=0
        ), use_container_width=True
    )

    return

def spent_per_product(df, keyword=None):
    products = df['ProductName'].unique()

    orders = [
        len(df.loc[
            df['ProductName'] == elem
        ])
        for elem in products
    ]

    totals = [
        df.loc[
            df['ProductName'] == elem
        ]['ItemTotal'].sum()
        for elem in products
    ]

    chart_data = pd.DataFrame({
        'Prodotti': products,
        'Ordini': orders,
        'Totale': totals
    })
    
    st.subheader("Ordini e fatturato per prodotti")
    st.write(chart_data.sort_values(by=['Prodotti']).reset_index(drop=True))

    return

def spent_per_product_category(df):
    unique_categories = sorted(pd.unique(df['Category'].str.split(';', expand=True).stack()))
    
    orders = [
        len(df.loc[
            df['Category'].str.contains(category, na=False)
        ])
        for category in unique_categories
    ]

    totals = [
        df.loc[
            df['Category'].str.contains(category, na=False)
        ]['ItemTotal'].sum()
        for category in unique_categories
    ]

    chart_data = pd.DataFrame({
        'Categorie': unique_categories,
        'Ordini': orders,
        'Totale': totals
    })
    
    st.subheader("Fatturato per categoria")
    st.write(chart_data)

# ------------------------------
#             CORE
# ------------------------------

# def facebook_analysis(pixel_id, start_date, end_date):
#     dataset = pixel_url_data(pixel_id, start_date, end_date)

    # return

def woocommerce_analysis(source, start_date, end_date, status, status_str):
    if source == "":
        st.error('Errore: Inserire la fonte da cui recuperare i dati')
        return
    elif start_date > end_date:
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
    
    st.subheader("Dati in oggetto")
    if status == "":
        status = "Tutti"
    st.success("Ordini dal `%s` al `%s`\n\nStato degli ordini: `%s`" % (start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y"), status_str))

    # ---------- ORDINI ----------
    st.title("Analisi degli ordini")

    st.subheader("Dataset")
    with st.spinner("Analisi degli ordini..."):
        orders = orders_retrieving(df)
        st.write(orders)

    st.title("Analisi degli ordini e del fatturato")

    with st.spinner("Analisi degli ordini per giorno..."):
        daily_order(orders)
    
    with st.spinner("Analisi della spesa per fasce di prezzo..."):
        spending_ranges(orders)
    
    with st.spinner("Analisi della spesa per fascia di età..."):
        spent_per_age(orders)

    # ---------- PRODOTTI ----------
    st.title("Analisi dei prodotti")
    
    st.subheader("Dataset")
    with st.spinner("Analisi dei prodotti..."):
        products = products_retrieving(df)
        st.write(products)

    st.title("Analisi dei prodotti e del fatturato")

    with st.spinner("Analisi dei prodotti per acquisto..."):
        spent_per_product(products)
    
    with st.spinner("Analisi delle categorie prodotto per acquisto..."):
        spent_per_product_category(products)

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

env = environ.Env(
    DEBUG = (bool, False)
)

DEBUG_MODE = env.bool('DEBUG_MODE', default=False)

if DEBUG_MODE:
    st.subheader("Inserire il token di accesso di Facebook")
    pixel_id = st.text_input("Access token")
    st.subheader("Inserire la fonte")
    source = st.text_input("Fonte")
else:
    source = st.secrets["url"]
    pixel_id = st.secrets["pixel_id"]

st.subheader("Selezionare il periodo desiderato")
start_date = st.date_input("Inizio", (datetime.today() - timedelta(days=31)))
end_date = st.date_input("Fine", (datetime.today() - timedelta(days=1)))

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
    # facebook_analysis(pixel_id, start_date, end_date)
    woocommerce_analysis(source, start_date, end_date, status, status_str)
