#!/usr/bin/env python3
"""
Como usar:
  python3 previsao_demanda.py <pasta_ou_zip_de_csvs>

Exemplo:
  python3 previsao_demanda.py ../inputs/1-lh_nautical_csv.zip
"""

import os
import re
import sys
import zipfile
import tempfile
import shutil
import pandas as pd

PRODUTO_ALVO = "Bússola de Bordo 702"
FIM_DO_TREINO = "2025-12"       # ultimo mes usado para treinar o baseline
MESES_DE_TESTE = ["2026-01", "2026-02", "2026-03"]


def extrair_zip_se_precisar(caminho_de_entrada, pastas_temporarias):
    """Se for um .zip, extrai numa pasta temporaria e devolve essa pasta."""
    if os.path.isfile(caminho_de_entrada) and caminho_de_entrada.lower().endswith(".zip"):
        pasta_temporaria = tempfile.mkdtemp()
        with zipfile.ZipFile(caminho_de_entrada, "r") as arquivo_zip:
            arquivo_zip.extractall(pasta_temporaria)
        pastas_temporarias.append(pasta_temporaria)
        return pasta_temporaria
    return caminho_de_entrada


def encontrar_csv(pasta, nome_base):
    """Procura um arquivo .csv especifico dentro da pasta (e subpastas),
    pelo nome (sem extensao), ignorando maiusculas/minusculas."""
    for pasta_atual, _subpastas, arquivos in os.walk(pasta):
        if "__MACOSX" in pasta_atual:
            continue
        for nome_do_arquivo in arquivos:
            nome_sem_extensao = os.path.splitext(nome_do_arquivo)[0].lower()
            if nome_sem_extensao == nome_base.lower() and nome_do_arquivo.lower().endswith(".csv"):
                return os.path.join(pasta_atual, nome_do_arquivo)
    raise FileNotFoundError(f"Nao encontrei um arquivo '{nome_base}.csv' dentro de: {pasta}")


def montar_dataset_unificado(pasta_com_csvs):
    """
    Junta as 4 tabelas (products, product_variants, orders, order_items)
    e devolve so as linhas referentes ao produto alvo, com a data e a
    quantidade vendida de cada item.

    Observacao: o catalogo de produtos pode ter mais de um product_id
    com exatamente o mesmo nome (aconteceu com "Bussola de Bordo 702").
    Nesse caso, cada product_id e tratado como um produto DIFERENTE (nao
    soma um no outro) -- o script escolhe automaticamente o product_id
    que realmente tem historico de vendas, e avisa sobre o(s) outro(s).
    """
    products = pd.read_csv(encontrar_csv(pasta_com_csvs, "products"))
    product_variants = pd.read_csv(encontrar_csv(pasta_com_csvs, "product_variants"))
    orders = pd.read_csv(encontrar_csv(pasta_com_csvs, "orders"))
    order_items = pd.read_csv(encontrar_csv(pasta_com_csvs, "order_items"))

    produtos_com_esse_nome = products[products["name"] == PRODUTO_ALVO]
    if produtos_com_esse_nome.empty:
        raise ValueError(f"Produto '{PRODUTO_ALVO}' nao encontrado em products.csv")

    if len(produtos_com_esse_nome) > 1:
        print(f"AVISO: existem {len(produtos_com_esse_nome)} produtos diferentes com o nome '{PRODUTO_ALVO}':")
        print(produtos_com_esse_nome[["id", "brand_id", "category_id", "created_at"]].to_string(index=False))

    variantes_do_produto = product_variants[product_variants["product_id"].isin(produtos_com_esse_nome["id"])]

    itens_do_produto = order_items[order_items["product_variant_id"].isin(variantes_do_produto["id"])]
    itens_do_produto = itens_do_produto.merge(
        variantes_do_produto[["id", "product_id"]].rename(columns={"id": "product_variant_id"}),
        on="product_variant_id",
    )

    if len(produtos_com_esse_nome) > 1:
        vendas_por_product_id = itens_do_produto.groupby("product_id")["quantity"].sum()
        vendas_por_product_id = vendas_por_product_id.reindex(produtos_com_esse_nome["id"], fill_value=0)
        print("\nUnidades vendidas (todo o historico), por product_id candidato:")
        print(vendas_por_product_id.to_string())

        product_id_escolhido = vendas_por_product_id.idxmax()
        ignorados = [pid for pid in produtos_com_esse_nome["id"] if pid != product_id_escolhido]
        print(f"\n-> Usando product_id={product_id_escolhido}, o de maior volume de vendas.")
        print(f"   ATENCAO: product_id(s) {ignorados} tambem tem vendas reais registradas")
        print("   (nao e um cadastro vazio) -- essa e uma escolha de criterio (maior volume),")
        print("   nao uma eliminacao por falta de dado. Vale confirmar com o time de produto")
        print("   se os dois cadastros realmente deveriam ser o mesmo item.\n")

        itens_do_produto = itens_do_produto[itens_do_produto["product_id"] == product_id_escolhido]

    dataset = itens_do_produto.merge(
        orders[["id", "placed_at"]],
        left_on="order_id",
        right_on="id",
        suffixes=("", "_pedido"),
    )

    dataset["placed_at"] = pd.to_datetime(dataset["placed_at"])
    dataset["mes"] = dataset["placed_at"].dt.to_period("M").astype(str)

    return dataset[["mes", "quantity"]]


def montar_serie_mensal(dataset, primeiro_mes, ultimo_mes):
    """
    Soma a quantidade vendida por mes, preenchendo com 0 os meses que
    nao tiveram nenhuma venda (para nao "pular" meses no calendario).
    """
    vendas_por_mes = dataset.groupby("mes")["quantity"].sum()

    todos_os_meses = pd.period_range(primeiro_mes, ultimo_mes, freq="M").astype(str)
    serie_completa = vendas_por_mes.reindex(todos_os_meses, fill_value=0)

    return serie_completa


def prever_media_movel_3_meses(serie_mensal, meses_para_prever):
    """
    Para cada mes a prever, calcula a media dos 3 meses anteriores a
    ele na serie (usando so dados que ja existiam antes daquele mes).
    """
    previsoes = {}
    for mes in meses_para_prever:
        posicao = serie_mensal.index.get_loc(mes)
        ultimos_3_meses = serie_mensal.iloc[posicao - 3: posicao]
        previsoes[mes] = ultimos_3_meses.mean()
    return pd.Series(previsoes)


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 previsao_demanda.py <pasta_ou_zip_de_csvs>")
        sys.exit(1)

    caminho_de_entrada = sys.argv[1]

    pastas_temporarias = []
    pasta_com_csvs = extrair_zip_se_precisar(caminho_de_entrada, pastas_temporarias)

    dataset = montar_dataset_unificado(pasta_com_csvs)

    primeiro_mes = dataset["mes"].min()
    serie_mensal = montar_serie_mensal(dataset, primeiro_mes, MESES_DE_TESTE[-1])

    print(f"Produto analisado: {PRODUTO_ALVO}")
    print(f"\nVendas mensais (unidades) - historico completo:")
    print(serie_mensal.to_string())

    previsoes = prever_media_movel_3_meses(serie_mensal, MESES_DE_TESTE)
    reais = serie_mensal.loc[MESES_DE_TESTE]

    comparacao = pd.DataFrame({
        "vendido_real": reais,
        "previsto_baseline": previsoes.round(1),
    })
    comparacao["erro_absoluto"] = (comparacao["vendido_real"] - comparacao["previsto_baseline"]).abs()

    print(f"\nComparacao no periodo de teste (1o trimestre de 2026):")
    print(comparacao.to_string())

    mae = comparacao["erro_absoluto"].mean()
    media_vendida_no_teste = comparacao["vendido_real"].mean()
    erro_percentual = (mae / media_vendida_no_teste * 100) if media_vendida_no_teste > 0 else float("nan")

    print(f"\nMAE (Mean Absolute Error): {mae:.2f} unidades")
    print(f"Media vendida no periodo de teste: {media_vendida_no_teste:.2f} unidades")
    print(f"MAE como % da media vendida: {erro_percentual:.1f}%")

    print("\n--- Respostas ---")
    print("a) O baseline e adequado para esse produto?")
    if erro_percentual < 20:
        print(f"   Sim, parece adequado: o erro medio (MAE) equivale a apenas {erro_percentual:.1f}%")
        print("   da media vendida no periodo, um desvio pequeno para uma decisao de compra.")
    else:
        print(f"   Nao parece adequado: o erro medio (MAE) equivale a {erro_percentual:.1f}%")
        print("   da media vendida no periodo, um desvio grande demais para decidir compra com")
        print("   seguranca so com esse baseline.")

    print("\nb) Limitacao do metodo:")
    print("   A media movel so enxerga o volume de vendas que aconteceu de fato -- ela nao")
    print("   distingue 'baixa demanda' de 'produto fora de estoque'. Se o produto ficou sem")
    print("   estoque em algum mes do historico usado no calculo, a media fica artificialmente")
    print("   baixa (porque venda zero por falta de produto conta igual a venda zero por falta")
    print("   de interesse do cliente), gerando uma previsao subestimada -- exatamente o tipo de")
    print("   problema que causou a ruptura de estoque dos Coletes Salva-Vidas no verao passado.")
    print("   Alem disso, o metodo nao captura tendencia de crescimento nem sazonalidade (ex:")
    print("   picos de venda em datas comemorativas ou epoca de verao).")

    for pasta in pastas_temporarias:
        shutil.rmtree(pasta, ignore_errors=True)


if __name__ == "__main__":
    main()