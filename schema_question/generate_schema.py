#!/usr/bin/env python3
"""
generate_schema.py
-------------------
Le os arquivos CSV de uma pasta (ou de um .zip) e gera um arquivo
schema.sql com os comandos CREATE TABLE (PostgreSQL), um para cada CSV.

O tipo de cada coluna e descoberto olhando os valores dela no CSV.

So usa biblioteca padrao do Python (csv, os, re, sys, zipfile, tempfile,
shutil, datetime). Nao usa pandas nem nenhuma lib de terceiros.

Como usar:
  python3 generate_schema.py <pasta_ou_zip_de_entrada> <arquivo_sql_de_saida>

Exemplo:
  python3 generate_schema.py ../inputs/1-lh_nautical_csv.zip ../outputs/schema.sql
"""

import csv
import os
import re
import sys
import zipfile
import tempfile
import shutil
from datetime import datetime

# Formatos de data e hora que o script tenta reconhecer nos valores do CSV
FORMATOS_DE_DATA = ["%Y-%m-%d", "%d/%m/%Y"]
FORMATOS_DE_DATA_HORA = ["%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"]

# Valores que vamos considerar "vazios" (equivalente a NULL no banco)
VALORES_NULOS = {"", "null", "none", "n/a"}

# Valores que vamos considerar booleanos
# obs: "0" e "1" ficam de fora de proposito, para nao confundir uma coluna
# numerica (ex: quantidade) com uma coluna booleana
VALORES_VERDADEIRO = {"true", "sim"}
VALORES_FALSO = {"false", "nao", "não"}


def limpar_nome(nome_original):
    """
    Transforma um nome de arquivo ou coluna em um nome valido para o
    PostgreSQL: minusculo, so letras/numeros/underscore, sem espaco.
    Exemplo: "Data Criação" -> "data_criacao"
    """
    nome = nome_original.strip().lower()

    # troca acentos comuns por letra sem acento
    substituicoes = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "õ": "o", "ô": "o",
        "ú": "u",
        "ç": "c",
    }
    for letra_com_acento, letra_sem_acento in substituicoes.items():
        nome = nome.replace(letra_com_acento, letra_sem_acento)

    # troca qualquer caractere que nao seja letra/numero por "_"
    nome = re.sub(r"[^a-z0-9_]+", "_", nome)
    nome = re.sub(r"_+", "_", nome).strip("_")

    if nome == "":
        nome = "coluna"

    return nome


def valor_e_nulo(valor):
    return valor.strip().lower() in VALORES_NULOS


def valor_e_booleano(valor):
    valor = valor.strip().lower()
    return valor in VALORES_VERDADEIRO or valor in VALORES_FALSO


def valor_e_inteiro(valor):
    return re.fullmatch(r"-?\d+", valor.strip()) is not None


def valor_e_numero_decimal(valor):
    valor = valor.strip()
    # aceita tanto 10.50 (padrao) quanto 10,50 (formato BR)
    return re.fullmatch(r"-?\d+[.,]\d+", valor) is not None


def valor_e_data(valor):
    for formato in FORMATOS_DE_DATA:
        try:
            datetime.strptime(valor.strip(), formato)
            return True
        except ValueError:
            pass
    return False


def valor_e_data_hora(valor):
    for formato in FORMATOS_DE_DATA_HORA:
        try:
            datetime.strptime(valor.strip(), formato)
            return True
        except ValueError:
            pass
    return False


def descobrir_tipo_da_coluna(valores):
    """
    Recebe todos os valores de uma coluna (lista de strings) e devolve
    uma tupla (tipo_no_postgres, aceita_nulo).
    """
    valores_preenchidos = [v for v in valores if not valor_e_nulo(v)]
    aceita_nulo = len(valores_preenchidos) < len(valores)

    # coluna totalmente vazia -> usa TEXT como opcao segura
    if len(valores_preenchidos) == 0:
        return "TEXT", True

    if all(valor_e_booleano(v) for v in valores_preenchidos):
        return "BOOLEAN", aceita_nulo

    if all(valor_e_inteiro(v) for v in valores_preenchidos):
        # o tipo INTEGER do Postgres so aguenta ate 2147483647.
        # numeros maiores que isso (ex: CNPJ, codigo de barras) precisam
        # de BIGINT, senao o carregamento dos dados da erro.
        maior_valor = max(abs(int(v.strip())) for v in valores_preenchidos)
        if maior_valor > 9223372036854775807:
            # numero grande demais ate para BIGINT (ex: chave de acesso de
            # nota fiscal, que tem 44 digitos). Nesse caso nao e um numero
            # de verdade, e sim um codigo/identificador -> trata como TEXT
            return "TEXT", aceita_nulo
        if maior_valor > 2147483647:
            return "BIGINT", aceita_nulo
        return "INTEGER", aceita_nulo

    if all(valor_e_inteiro(v) or valor_e_numero_decimal(v) for v in valores_preenchidos):
        return "NUMERIC", aceita_nulo

    if all(valor_e_data(v) for v in valores_preenchidos):
        return "DATE", aceita_nulo

    if all(valor_e_data_hora(v) for v in valores_preenchidos):
        return "TIMESTAMP", aceita_nulo

    return "TEXT", aceita_nulo


def ler_csv(caminho_do_arquivo):
    """Le um CSV e devolve (cabecalho, linhas_de_dados)."""
    with open(caminho_do_arquivo, "r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.reader(arquivo)
        todas_as_linhas = list(leitor)

    cabecalho = todas_as_linhas[0]
    linhas_de_dados = todas_as_linhas[1:]
    return cabecalho, linhas_de_dados


def pegar_valores_da_coluna(linhas_de_dados, indice_da_coluna):
    """Extrai todos os valores de uma coluna especifica, pelo indice dela."""
    valores = []
    for linha in linhas_de_dados:
        if indice_da_coluna < len(linha):
            valores.append(linha[indice_da_coluna])
        else:
            valores.append("")  # linha mais curta que o cabecalho
    return valores


def gerar_create_table(nome_da_tabela, cabecalho, linhas_de_dados):
    """Monta o texto do comando CREATE TABLE para um CSV."""
    linhas_de_colunas = []

    for indice, nome_da_coluna_original in enumerate(cabecalho):
        nome_da_coluna = limpar_nome(nome_da_coluna_original)
        valores = pegar_valores_da_coluna(linhas_de_dados, indice)
        tipo, aceita_nulo = descobrir_tipo_da_coluna(valores)

        texto_nulo = "" if aceita_nulo else " NOT NULL"
        linhas_de_colunas.append(f"    {nome_da_coluna} {tipo}{texto_nulo}")

    colunas_formatadas = ",\n".join(linhas_de_colunas)
    return f"CREATE TABLE IF NOT EXISTS {nome_da_tabela} (\n{colunas_formatadas}\n);"


def extrair_zip_se_precisar(caminho_de_entrada, pastas_temporarias):
    """
    Se caminho_de_entrada for um .zip, extrai numa pasta temporaria e
    devolve essa pasta. Se for uma pasta normal, so devolve ela mesma.
    """
    if os.path.isfile(caminho_de_entrada) and caminho_de_entrada.lower().endswith(".zip"):
        pasta_temporaria = tempfile.mkdtemp()
        with zipfile.ZipFile(caminho_de_entrada, "r") as arquivo_zip:
            arquivo_zip.extractall(pasta_temporaria)
        pastas_temporarias.append(pasta_temporaria)
        return pasta_temporaria

    return caminho_de_entrada


def encontrar_arquivos_csv(pasta):
    """Procura todos os arquivos .csv dentro da pasta (e subpastas)."""
    arquivos_encontrados = []
    for pasta_atual, _subpastas, arquivos in os.walk(pasta):
        # pula a pasta de metadados que o macOS as vezes cria dentro de zips
        if "__MACOSX" in pasta_atual:
            continue
        for nome_do_arquivo in arquivos:
            # pula arquivos ocultos de metadado (ex: "._tabela1.csv")
            if nome_do_arquivo.startswith("._"):
                continue
            if nome_do_arquivo.lower().endswith(".csv"):
                caminho_completo = os.path.join(pasta_atual, nome_do_arquivo)
                arquivos_encontrados.append(caminho_completo)
    return sorted(arquivos_encontrados)


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 generate_schema.py <entrada> <saida.sql>")
        print("Exemplo: python3 generate_schema.py ../inputs/dados.zip ../outputs/schema.sql")
        sys.exit(1)

    caminho_de_entrada = sys.argv[1]
    caminho_de_saida = sys.argv[2]

    pastas_temporarias = []
    pasta_com_csvs = extrair_zip_se_precisar(caminho_de_entrada, pastas_temporarias)
    arquivos_csv = encontrar_arquivos_csv(pasta_com_csvs)

    if not arquivos_csv:
        print(f"Nenhum arquivo .csv encontrado em: {caminho_de_entrada}")
        sys.exit(1)

    blocos_sql = []
    for caminho_csv in arquivos_csv:
        nome_do_arquivo = os.path.basename(caminho_csv)
        nome_da_tabela = limpar_nome(os.path.splitext(nome_do_arquivo)[0])

        print(f"Lendo {nome_do_arquivo} -> tabela '{nome_da_tabela}'")

        cabecalho, linhas_de_dados = ler_csv(caminho_csv)
        comando_sql = gerar_create_table(nome_da_tabela, cabecalho, linhas_de_dados)

        bloco = f"-- Tabela gerada a partir de: {nome_do_arquivo}\n{comando_sql}"
        blocos_sql.append(bloco)

    # cria a pasta de saida automaticamente, se ela ainda nao existir
    pasta_de_saida = os.path.dirname(caminho_de_saida)
    if pasta_de_saida != "" and not os.path.isdir(pasta_de_saida):
        os.makedirs(pasta_de_saida)

    with open(caminho_de_saida, "w", encoding="utf-8") as arquivo_de_saida:
        arquivo_de_saida.write("\n\n".join(blocos_sql))
        arquivo_de_saida.write("\n")

    for pasta in pastas_temporarias:
        shutil.rmtree(pasta, ignore_errors=True)

    print(f"\nPronto! {len(arquivos_csv)} tabela(s) escritas em {caminho_de_saida}")


if __name__ == "__main__":
    main()