import streamlit as st
import pandas as pd
import plotly.express as px
import snowflake.connector


st.set_page_config(
    page_title="COVID-19 Dashboard",
    page_icon="🦠",
    layout="wide"
)


@st.cache_data
def carregar_dados():
    conn = snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"]
    )

    query = """
        SELECT
            LOCATION,
            DATE,
            NEW_CASES,
            TOTAL_DEATHS,
            PEOPLE_VACCINATED,
            POPULATION
        FROM COVID_DATA
        ORDER BY DATE
    """

    df = pd.read_sql(query, conn)
    conn.close()

    df.columns = df.columns.str.lower()
    df["date"] = pd.to_datetime(df["date"])

    return df


def calcular_kpis(df_filtrado, ultimo_registro):
    total_casos = df_filtrado["new_cases"].sum()
    total_obitos = ultimo_registro["total_deaths"].sum()
    total_vacinados = ultimo_registro["people_vaccinated"].sum()
    return total_casos, total_obitos, total_vacinados


def exibir_kpis(total_casos, total_obitos, total_vacinados):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total de casos", f"{total_casos:,.0f}")

    with col2:
        st.metric("Total de óbitos", f"{total_obitos:,.0f}")

    with col3:
        st.metric("Pessoas vacinadas", f"{total_vacinados:,.0f}")


def grafico_evolucao_casos(df_filtrado):
    st.subheader("Evolução de casos novos por país")

    fig = px.line(
        df_filtrado,
        x="date",
        y="new_cases",
        color="location",
        title="Evolução de novos casos"
    )

    st.plotly_chart(fig, use_container_width=True)


def grafico_obitos_por_pais(ultimo_registro):
    st.subheader("Total de óbitos por país")

    fig = px.bar(
        ultimo_registro,
        x="location",
        y="total_deaths",
        title="Total de óbitos por país"
    )

    st.plotly_chart(fig, use_container_width=True)


def grafico_proporcao_vacinados(ultimo_registro):
    st.subheader("Proporção de vacinados")

    vacinados = ultimo_registro["people_vaccinated"].fillna(0).sum()
    populacao = ultimo_registro["population"].fillna(0).sum()
    nao_vacinados = max(populacao - vacinados, 0)

    df_pizza = pd.DataFrame({
        "Categoria": ["Pessoas vacinadas", "Pessoas não vacinadas"],
        "Quantidade": [vacinados, nao_vacinados]
    })

    fig = px.pie(
        df_pizza,
        names="Categoria",
        values="Quantidade",
        title="Proporção de pessoas vacinadas"
    )

    st.plotly_chart(fig, use_container_width=True)


def grafico_populacao_casos(df_filtrado):
    st.subheader("População x Total de casos")

    casos_por_pais = (
        df_filtrado
        .groupby("location")
        .agg(
            population=("population", "max"),
            total_cases=("new_cases", "sum")
        )
        .reset_index()
    )

    fig = px.scatter(
        casos_por_pais,
        x="population",
        y="total_cases",
        size="population",
        color="location",
        hover_name="location",
        title="População x Total de casos"
    )

    st.plotly_chart(fig, use_container_width=True)


def exibir_dados_brutos(df_filtrado):
    st.subheader("Dados Brutos")

    st.dataframe(df_filtrado, use_container_width=True)

    csv = df_filtrado.to_csv(index=False)

    st.download_button(
        label="Baixar dados em CSV",
        data=csv,
        file_name="covid_dados.csv",
        mime="text/csv"
    )


def main():
    df = carregar_dados()

    st.title("Dashboard COVID-19")
    st.write(
        "Dashboard desenvolvido com Streamlit, Snowflake, "
        "GitHub e dados públicos da Our World in Data."
    )

    paises = sorted(df["location"].unique())
    paises_selecionados = st.multiselect(
        "Selecione os países:",
        paises,
        default=paises
    )

    df_filtrado = df[df["location"].isin(paises_selecionados)].copy()
    df_filtrado = df_filtrado.sort_values(["location", "date"])

    df_filtrado["total_deaths"] = (
        df_filtrado.groupby("location")["total_deaths"].ffill()
    )
    df_filtrado["people_vaccinated"] = (
        df_filtrado.groupby("location")["people_vaccinated"].ffill()
    )

    tab_dashboard, tab_dados = st.tabs(["Dashboard", "Dados Brutos"])

    with tab_dashboard:
        ultimo_registro = (
            df_filtrado
            .groupby("location")
            .tail(1)
        )

        total_casos, total_obitos, total_vacinados = calcular_kpis(
            df_filtrado, ultimo_registro
        )
        exibir_kpis(total_casos, total_obitos, total_vacinados)

        grafico_evolucao_casos(df_filtrado)
        grafico_obitos_por_pais(ultimo_registro)
        grafico_proporcao_vacinados(ultimo_registro)
        grafico_populacao_casos(df_filtrado)

    with tab_dados:
        exibir_dados_brutos(df_filtrado)


if __name__ == "__main__":
    main()