import io
import os
import zipfile
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="LH Nautical | Analytics Dashboard",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Helpers
# -----------------------------
@st.cache_data(show_spinner=False)
def load_zip(uploaded_bytes):
    tables = {}
    with zipfile.ZipFile(io.BytesIO(uploaded_bytes)) as z:
        for name in z.namelist():
            if not name.lower().endswith(".csv"):
                continue
            key = os.path.splitext(os.path.basename(name))[0].lower()
            if key not in tables:
                with z.open(name) as f:
                    tables[key] = pd.read_csv(f)
    return tables

@st.cache_data(show_spinner=False)
def build_model(t):
    orders = t["orders"].copy()
    orders["placed_at"] = pd.to_datetime(orders["placed_at"], errors="coerce")
    orders["created_at"] = pd.to_datetime(orders["created_at"], errors="coerce")

    order_items = t["order_items"].copy()
    products = t["products"].copy()
    variants = t["product_variants"].copy()
    categories = t["categories"].copy()
    customers = t["customers"].copy()

    oi = (
        order_items
        .merge(
            orders[["id", "customer_id", "channel", "status", "placed_at", "total"]],
            left_on="order_id", right_on="id", suffixes=("", "_order")
        )
        .merge(
            variants[["id", "product_id", "sale_price", "cost_price", "is_active"]],
            left_on="product_variant_id", right_on="id", suffixes=("", "_variant")
        )
        .merge(
            products[["id", "name", "brand_id", "category_id"]],
            left_on="product_id", right_on="id", suffixes=("", "_product")
        )
        .merge(
            categories[["id", "name"]],
            left_on="category_id", right_on="id", suffixes=("", "_category")
        )
    )
    oi["revenue"] = oi["line_total"]
    oi["estimated_cost"] = oi["quantity"] * oi["cost_price"]
    oi["estimated_margin"] = oi["revenue"] - oi["estimated_cost"]
    oi["margin_pct"] = np.where(
        oi["revenue"] != 0, oi["estimated_margin"] / oi["revenue"], np.nan
    )

    customer_summary = (
        orders.groupby("customer_id")
        .agg(
            revenue=("total", "sum"),
            orders=("id", "count"),
            avg_ticket=("total", "mean"),
        )
        .reset_index()
    )
    customer_summary["avg_ticket"] = customer_summary["avg_ticket"].round(2)

    product_summary = (
        oi.groupby(["product_id", "name", "category_id"])
        .agg(
            units=("quantity", "sum"),
            revenue=("revenue", "sum"),
            estimated_margin=("estimated_margin", "sum"),
        )
        .reset_index()
    )
    product_summary["margin_pct"] = np.where(
        product_summary["revenue"] != 0,
        product_summary["estimated_margin"] / product_summary["revenue"],
        np.nan,
    )

    return orders, oi, product_summary, customer_summary

def money(x):
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def integer(x):
    return f"{int(round(x)):,}".replace(",", ".")

# -----------------------------
# Load
# -----------------------------
st.title("⚓ LH Nautical — Analytics Dashboard")
st.caption(
    "Visão analítica do case Indicium. O dashboard lê diretamente os CSVs originais "
    "e foi estruturado para comunicar performance, clientes, produtos, demanda e qualidade."
)

with st.sidebar:
    st.header("Dados")
    uploaded = st.file_uploader(
        "Envie o ZIP dos CSVs",
        type=["zip"],
        help="Use o arquivo 1-lh_nautical_csv.zip entregue no desafio.",
    )

if uploaded is None:
    st.info("Envie o ZIP dos CSVs na barra lateral para iniciar a análise.")
    st.stop()

tables = load_zip(uploaded.getvalue())
required = {"orders", "order_items", "products", "product_variants", "categories"}
missing = required - set(tables)
if missing:
    st.error(f"Tabelas obrigatórias ausentes: {sorted(missing)}")
    st.stop()

orders, oi, product_summary, customer_summary = build_model(tables)

# -----------------------------
# Filters
# -----------------------------
with st.sidebar:
    st.header("Filtros")

    min_date = orders["placed_at"].min().date()
    max_date = orders["placed_at"].max().date()
    date_range = st.date_input(
        "Período",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    channels = sorted(orders["channel"].dropna().unique().tolist())
    selected_channels = st.multiselect("Canal", channels, default=channels)

    statuses = sorted(orders["status"].dropna().unique().tolist())
    selected_statuses = st.multiselect("Status do pedido", statuses, default=statuses)

mask = (
    orders["placed_at"].dt.date.between(start_date, end_date)
    & orders["channel"].isin(selected_channels)
    & orders["status"].isin(selected_statuses)
)
filtered_orders = orders.loc[mask].copy()

filtered_oi = oi[oi["order_id"].isin(filtered_orders["id"])].copy()

# -----------------------------
# Executive KPIs
# -----------------------------
revenue = filtered_orders["total"].sum()
order_count = len(filtered_orders)
ticket = filtered_orders["total"].mean() if order_count else 0
customers = filtered_orders["customer_id"].nunique()
units = filtered_oi["quantity"].sum()
margin = filtered_oi["estimated_margin"].sum()
margin_pct = margin / filtered_oi["revenue"].sum() if filtered_oi["revenue"].sum() else np.nan

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Faturamento", money(revenue))
c2.metric("Pedidos", integer(order_count))
c3.metric("Ticket médio", money(ticket))
c4.metric("Clientes", integer(customers))
c5.metric("Unidades", integer(units))
c6.metric("Margem estimada", f"{margin_pct:.1%}" if pd.notna(margin_pct) else "n/a")

tabs = st.tabs([
    "Visão executiva",
    "Vendas",
    "Clientes",
    "Produtos",
    "Previsão",
    "Recomendação",
    "Qualidade dos dados",
])

# -----------------------------
# Executive
# -----------------------------
with tabs[0]:
    st.subheader("Resumo executivo")

    monthly = (
        filtered_orders.set_index("placed_at")
        .resample("ME")["total"].sum()
        .rename("faturamento")
        .to_frame()
    )
    monthly.index = monthly.index.strftime("%Y-%m")
    st.markdown("### Evolução do faturamento")
    st.line_chart(monthly)

    left, right = st.columns(2)

    with left:
        st.markdown("### Faturamento por canal")
        channel = (
            filtered_orders.groupby("channel")
            .agg(faturamento=("total", "sum"), pedidos=("id", "count"))
            .sort_values("faturamento", ascending=False)
        )
        st.bar_chart(channel["faturamento"])

    with right:
        st.markdown("### Principais categorias")
        cat = (
            filtered_oi.groupby("name_category")["revenue"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )
        st.bar_chart(cat)

    st.markdown("### Leitura analítica")
    st.info(
        "O negócio combina um canal e-commerce de maior escala com vendas físicas (POS). "
        "A leitura deve considerar simultaneamente volume, ticket e mix de produtos, "
        "evitando avaliar performance apenas pelo faturamento bruto."
    )

# -----------------------------
# Sales
# -----------------------------
with tabs[1]:
    st.subheader("Performance comercial")

    left, right = st.columns(2)
    with left:
        st.markdown("### Pedidos por canal")
        st.bar_chart(filtered_orders["channel"].value_counts())

    with right:
        st.markdown("### Ticket médio por canal")
        ticket_channel = filtered_orders.groupby("channel")["total"].mean().sort_values(ascending=False)
        st.bar_chart(ticket_channel)

    daily = filtered_orders.set_index("placed_at").resample("D")["total"].sum()
    st.markdown("### Série diária de faturamento")
    st.line_chart(daily)

    st.markdown("### Dia da semana — POS")
    pos = filtered_orders[filtered_orders["channel"] == "pos"].copy()
    if not pos.empty:
        pos["weekday"] = pos["placed_at"].dt.day_name()
        order_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        labels = {
            "Monday":"Segunda-feira", "Tuesday":"Terça-feira", "Wednesday":"Quarta-feira",
            "Thursday":"Quinta-feira", "Friday":"Sexta-feira", "Saturday":"Sábado", "Sunday":"Domingo"
        }
        wd = pos.groupby("weekday")["total"].sum().reindex(order_days).rename(index=labels)
        st.bar_chart(wd)

# -----------------------------
# Customers
# -----------------------------
with tabs[2]:
    st.subheader("Clientes e fidelização")

    cs = (
        filtered_orders.groupby("customer_id")
        .agg(
            faturamento=("total", "sum"),
            pedidos=("id", "count"),
            ticket_medio=("total", "mean"),
        )
        .reset_index()
    )
    cs["ticket_medio"] = cs["ticket_medio"].round(2)

    # Category diversity
    diversity = (
        filtered_oi.groupby("customer_id")["category_id"]
        .nunique()
        .rename("categorias_distintas")
        .reset_index()
    )
    cs = cs.merge(diversity, on="customer_id", how="left").fillna({"categorias_distintas": 0})

    top_customers = cs.sort_values("faturamento", ascending=False).head(15)
    st.markdown("### Top clientes por faturamento")
    st.bar_chart(top_customers.set_index("customer_id")["faturamento"])
    st.dataframe(
        top_customers[
            ["customer_id", "faturamento", "pedidos", "ticket_medio", "categorias_distintas"]
        ],
        hide_index=True,
        use_container_width=True,
    )

    elite = cs[cs["categorias_distintas"] >= 13].sort_values(
        ["ticket_medio", "customer_id"], ascending=[False, True]
    ).head(10)

    st.markdown("### Clientes fiéis: 13+ categorias distintas")
    st.caption(
        "Critério reproduzido da questão do case. O ranking abaixo prioriza ticket médio."
    )
    st.dataframe(elite, hide_index=True, use_container_width=True)

# -----------------------------
# Products
# -----------------------------
with tabs[3]:
    st.subheader("Produtos, mix e margem estimada")

    ps = (
        filtered_oi.groupby(["product_id", "name", "category_id"])
        .agg(
            unidades=("quantity", "sum"),
            faturamento=("revenue", "sum"),
            margem_estimada=("estimated_margin", "sum"),
        )
        .reset_index()
    )
    ps["margem_pct"] = np.where(
        ps["faturamento"] != 0, ps["margem_estimada"] / ps["faturamento"], np.nan
    )

    left, right = st.columns(2)
    with left:
        st.markdown("### Produtos por faturamento")
        st.bar_chart(ps.nlargest(15, "faturamento").set_index("name")["faturamento"])
    with right:
        st.markdown("### Produtos por unidades")
        st.bar_chart(ps.nlargest(15, "unidades").set_index("name")["unidades"])

    st.markdown("### Produtos com maior margem estimada")
    st.dataframe(
        ps.nlargest(20, "margem_estimada")[
            ["product_id", "name", "unidades", "faturamento", "margem_estimada", "margem_pct"]
        ],
        hide_index=True,
        use_container_width=True,
    )

# -----------------------------
# Forecast
# -----------------------------
with tabs[4]:
    st.subheader("Previsão de demanda — Bússola de Bordo 702")

    target_name = "Bússola de Bordo 702"
    targets = tables["products"][tables["products"]["name"] == target_name]
    variants = tables["product_variants"]

    if targets.empty:
        st.warning("Produto não encontrado.")
    else:
        target_variants = variants[variants["product_id"].isin(targets["id"])]
        ds = (
            tables["order_items"][tables["order_items"]["product_variant_id"].isin(target_variants["id"])]
            .merge(target_variants[["id", "product_id"]], left_on="product_variant_id", right_on="id")
            .merge(orders[["id", "placed_at"]], left_on="order_id", right_on="id")
        )
        ds["mes"] = pd.to_datetime(ds["placed_at"]).dt.to_period("M").astype(str)
        volume_by_product = ds.groupby("product_id")["quantity"].sum()
        chosen_id = volume_by_product.idxmax()
        ds = ds[ds["product_id"] == chosen_id]

        monthly = ds.groupby("mes")["quantity"].sum()
        idx = pd.period_range(monthly.index.min(), "2026-03", freq="M").astype(str)
        series = monthly.reindex(idx, fill_value=0)

        test_months = ["2026-01", "2026-02", "2026-03"]
        forecasts = {}
        for m in test_months:
            p = series.index.get_loc(m)
            forecasts[m] = series.iloc[p-3:p].mean()

        comp = pd.DataFrame({
            "Real": series.loc[test_months],
            "Baseline (média móvel 3M)": pd.Series(forecasts),
        })
        comp["Erro absoluto"] = (comp["Real"] - comp["Baseline (média móvel 3M)"]).abs()
        mae = comp["Erro absoluto"].mean()
        pct_error = mae / comp["Real"].mean()

        st.line_chart(series)
        st.dataframe(comp.round(2), use_container_width=True)

        a, b, c = st.columns(3)
        a.metric("MAE", f"{mae:.1f} unidades")
        b.metric("Erro / média do teste", f"{pct_error:.1%}")
        c.metric("Produto analisado", f"id {chosen_id}")

        st.warning(
            "Conclusão: o baseline de média móvel de 3 meses não é suficientemente confiável "
            "para decisão de compra neste produto. Além de não capturar tendência/sazonalidade, "
            "o método não distingue baixa demanda de ruptura de estoque."
        )

        if len(targets) > 1:
            st.info(
                f"Há {len(targets)} cadastros com o mesmo nome. O dashboard usa o cadastro "
                f"com maior volume histórico (id {chosen_id}) para evitar misturar SKUs distintos."
            )

# -----------------------------
# Recommendation
# -----------------------------
with tabs[5]:
    st.subheader("Recomendação — quem comprou Motor de Popa 1949 também levou")

    target_name = "Motor de Popa 1949"
    p = tables["products"]
    v = tables["product_variants"]
    ref_rows = p[p["name"] == target_name]

    if ref_rows.empty:
        st.warning("Produto de referência não encontrado.")
    else:
        compras = (
            tables["order_items"][["order_id", "product_variant_id"]]
            .merge(orders[["id", "customer_id"]].rename(columns={"id":"order_id"}), on="order_id")
            .merge(v[["id","product_id"]].rename(columns={"id":"product_variant_id"}), on="product_variant_id")
            .merge(p[["id","name"]].rename(columns={"id":"product_id"}), on="product_id")
            [["customer_id","product_id","name"]]
            .drop_duplicates(["customer_id","product_id"])
        )

        ref_id = compras[compras["name"] == target_name]["product_id"].iloc[0]
        matrix = compras.assign(comprou=1).pivot(
            index="customer_id", columns="product_id", values="comprou"
        ).fillna(0)

        co = matrix.T @ matrix
        norms = np.sqrt(np.diag(co))
        denom = np.outer(norms, norms)
        denom[denom == 0] = 1
        sim = pd.DataFrame(co.values / denom, index=co.index, columns=co.columns)

        top = sim[ref_id].drop(ref_id).sort_values(ascending=False).head(10)
        names = compras.drop_duplicates("product_id").set_index("product_id")["name"]
        ranking = pd.DataFrame({
            "Produto": names.reindex(top.index).values,
            "Similaridade de cosseno": top.values,
            "product_id": top.index,
        })

        st.caption(f"Matriz Cliente × Produto: {matrix.shape[0]} clientes × {matrix.shape[1]} produtos")
        st.bar_chart(ranking.set_index("Produto")["Similaridade de cosseno"])
        st.dataframe(ranking, hide_index=True, use_container_width=True)

        st.info(
            "A similaridade de cosseno mede afinidade de compra entre produtos com base "
            "na sobreposição de clientes. Ela é adequada como baseline de recomendação, "
            "mas pode ser complementada por frequência, recência, margem e contexto de categoria."
        )

# -----------------------------
# Data quality
# -----------------------------
with tabs[6]:
    st.subheader("Qualidade e riscos dos dados")

    dq = []
    for name, df in tables.items():
        nulls = int(df.isna().sum().sum())
        rows = len(df)
        dq.append({
            "tabela": name,
            "linhas": rows,
            "colunas": df.shape[1],
            "celulas_nulas": nulls,
            "percentual_nulo": nulls / (rows * df.shape[1]) if rows and df.shape[1] else 0,
        })
    dq = pd.DataFrame(dq).sort_values("percentual_nulo", ascending=False)
    st.dataframe(dq, hide_index=True, use_container_width=True)

    eda = {
        "Pedidos": len(orders),
        "Total mínimo": orders["total"].min(),
        "Total máximo": orders["total"].max(),
        "Total médio": orders["total"].mean(),
        "Nulos em total": int(orders["total"].isna().sum()),
        "Negativos em total": int((orders["total"] < 0).sum()),
    }
    st.markdown("### Checks da tabela orders")
    st.dataframe(pd.DataFrame([eda]), hide_index=True, use_container_width=True)

    st.markdown("### Achados relevantes")
    st.markdown(
        """
- Os maiores pedidos apresentam queda gradual, sem salto isolado que sugira erro de carga.
- Existem dois cadastros com o mesmo nome de **Bússola de Bordo 702**; o dashboard evita misturá-los e documenta o critério de seleção.
- A previsão simples tem erro relevante no período de teste, indicando que não deve ser usada isoladamente para compra.
- Uma análise de estoque deve separar baixa demanda de ruptura; vendas observadas iguais a zero não significam necessariamente ausência de demanda.
        """
    )

# -----------------------------
# Footer
# -----------------------------
st.divider()
st.caption(
    "Indicium Lighthouse Case · Dashboard analítico · Fonte: CSVs fornecidos no desafio"
)