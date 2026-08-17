#!/usr/bin/env python3
"""
recomendacao.py
-----------------
Sistema de recomendacao "quem comprou isso, tambem levou..." baseado em
similaridade de cosseno entre produtos, a partir do historico de compras
dos clientes.

Le os CSVs originais (products, product_variants, orders, order_items),
monta uma matriz binaria Cliente x Produto (1 = comprou pelo menos uma
vez, 0 = nao comprou), calcula a similaridade de cosseno entre cada par
de produtos, e mostra o ranking dos 5 produtos mais similares a um
produto de referencia.

Bibliotecas usadas:
  - pandas, numpy (bibliotecas externas: pip install pandas numpy)
  - os, sys, zipfile, tempfile, shutil (padrao do Python 3)

Como usar:
  python3 recomendacao.py <pasta_ou_zip_de_csvs>

Exemplo:
  python3 recomendacao.py ../inputs/1-lh_nautical_csv.zip
"""

import os
import sys
import zipfile
import tempfile
import shutil
import numpy as np
import pandas as pd

PRODUTO_REFERENCIA = "Motor de Popa 1949"
QUANTIDADE_NO_RANKING = 5


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
    """Procura um arquivo .csv especifico dentro da pasta (e subpastas)."""
    for pasta_atual, _subpastas, arquivos in os.walk(pasta):
        if "__MACOSX" in pasta_atual:
            continue
        for nome_do_arquivo in arquivos:
            nome_sem_extensao = os.path.splitext(nome_do_arquivo)[0].lower()
            if nome_sem_extensao == nome_base.lower() and nome_do_arquivo.lower().endswith(".csv"):
                return os.path.join(pasta_atual, nome_do_arquivo)
    raise FileNotFoundError(f"Nao encontrei um arquivo '{nome_base}.csv' dentro de: {pasta}")


def montar_tabela_de_compras(pasta_com_csvs):
    """
    Junta as 4 tabelas e devolve uma linha para cada combinacao unica
    de (cliente, produto) que ele comprou, ja com o nome do produto.
    """
    products = pd.read_csv(encontrar_csv(pasta_com_csvs, "products"))
    product_variants = pd.read_csv(encontrar_csv(pasta_com_csvs, "product_variants"))
    orders = pd.read_csv(encontrar_csv(pasta_com_csvs, "orders"))
    order_items = pd.read_csv(encontrar_csv(pasta_com_csvs, "order_items"))

    pedidos = orders[["id", "customer_id"]].rename(columns={"id": "order_id"})
    variantes = product_variants[["id", "product_id"]].rename(columns={"id": "product_variant_id"})
    produtos = products[["id", "name"]].rename(columns={"id": "product_id"})

    compras = order_items[["order_id", "product_variant_id"]]
    compras = compras.merge(pedidos, on="order_id")
    compras = compras.merge(variantes, on="product_variant_id")
    compras = compras.merge(produtos, on="product_id")

    return compras[["customer_id", "product_id", "name"]].drop_duplicates(
        subset=["customer_id", "product_id"]
    )


def montar_matriz_cliente_produto(tabela_de_compras):
    """
    Monta a matriz binaria Cliente x Produto:
    1 se o cliente comprou o produto pelo menos uma vez, 0 caso contrario.
    """
    matriz = tabela_de_compras.assign(comprou=1).pivot(
        index="customer_id", columns="product_id", values="comprou"
    )
    return matriz.fillna(0)


def calcular_similaridade_de_cosseno_entre_produtos(matriz_cliente_produto):
    """
    Calcula a similaridade de cosseno entre cada par de colunas (produtos)
    da matriz. Como os valores sao so 0 ou 1, o produto escalar entre dois
    produtos e simplesmente a quantidade de clientes que compraram os dois.
    """
    valores = matriz_cliente_produto.values  # formato: clientes x produtos

    produto_escalar = valores.T @ valores  # formato: produtos x produtos
    normas = np.sqrt(np.diag(produto_escalar))

    denominador = np.outer(normas, normas)
    # evita divisao por zero para produtos que ninguem comprou
    denominador[denominador == 0] = 1

    similaridade = produto_escalar / denominador

    return pd.DataFrame(
        similaridade,
        index=matriz_cliente_produto.columns,
        columns=matriz_cliente_produto.columns,
    )


def gerar_ranking_de_similares(matriz_similaridade, produto_id_referencia, mapa_id_para_nome, top_n):
    """Devolve os top_n produtos mais similares ao produto de referencia,
    excluindo ele mesmo do ranking."""
    similares = matriz_similaridade[produto_id_referencia].drop(index=produto_id_referencia)
    similares = similares.sort_values(ascending=False).head(top_n)

    ranking = similares.reset_index()
    ranking.columns = ["product_id", "similaridade"]
    ranking["nome_do_produto"] = ranking["product_id"].map(mapa_id_para_nome)
    ranking["similaridade"] = ranking["similaridade"].round(4)

    return ranking[["nome_do_produto", "similaridade", "product_id"]]


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 recomendacao.py <pasta_ou_zip_de_csvs>")
        sys.exit(1)

    caminho_de_entrada = sys.argv[1]

    pastas_temporarias = []
    pasta_com_csvs = extrair_zip_se_precisar(caminho_de_entrada, pastas_temporarias)

    tabela_de_compras = montar_tabela_de_compras(pasta_com_csvs)
    mapa_id_para_nome = tabela_de_compras.drop_duplicates("product_id").set_index("product_id")["name"]

    produto_referencia = tabela_de_compras[tabela_de_compras["name"] == PRODUTO_REFERENCIA]
    if produto_referencia.empty:
        raise ValueError(f"Produto '{PRODUTO_REFERENCIA}' nao encontrado (ou nunca foi comprado)")
    produto_id_referencia = produto_referencia["product_id"].iloc[0]

    matriz = montar_matriz_cliente_produto(tabela_de_compras)
    print(f"Matriz Cliente x Produto: {matriz.shape[0]} clientes x {matriz.shape[1]} produtos")

    similaridade = calcular_similaridade_de_cosseno_entre_produtos(matriz)

    ranking = gerar_ranking_de_similares(
        similaridade, produto_id_referencia, mapa_id_para_nome, QUANTIDADE_NO_RANKING
    )

    print(f"\nProduto de referencia: {PRODUTO_REFERENCIA}")
    print(f"\nTop {QUANTIDADE_NO_RANKING} produtos recomendados ('quem comprou isso, tambem levou'):")
    print(ranking.to_string(index=False))

    for pasta in pastas_temporarias:
        shutil.rmtree(pasta, ignore_errors=True)


if __name__ == "__main__":
    main()