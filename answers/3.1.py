#!/usr/bin/env python3
"""
Como usar:
  python3 load_csv.py <pasta_ou_zip_de_csvs> <caminho_do_schema.sql>

Exemplo:
  python3 load_csv.py ../inputs/1-lh_nautical_csv.zip ../outputs/schema.sql
"""

import os
import re
import sys
import zipfile
import tempfile
import shutil
import psycopg2
 
# Dados de conexao com o banco. Ajuste aqui se o seu Postgres estiver
# com outro usuario, senha, host, porta ou nome de banco.
DADOS_DE_CONEXAO = {
    "host": "localhost",
    "port": 5432,
    "dbname": "lighthouse",
    "user": "postgres",
    "password": "postgres",
}
 
 
def limpar_nome(nome_original):
    """
    Mesma funcao usada no generate_schema.py (Questao 2), repetida aqui
    para que o nome da tabela gerado bata exatamente com o nome usado
    no CREATE TABLE do schema.sql.
    """
    nome = nome_original.strip().lower()
 
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
 
    nome = re.sub(r"[^a-z0-9_]+", "_", nome)
    nome = re.sub(r"_+", "_", nome).strip("_")
 
    if nome == "":
        nome = "coluna"
 
    return nome
 
 
def extrair_zip_se_precisar(caminho_de_entrada, pastas_temporarias):
    """Se for um .zip, extrai numa pasta temporaria e devolve essa pasta."""
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
        if "__MACOSX" in pasta_atual:
            continue
        for nome_do_arquivo in arquivos:
            if nome_do_arquivo.startswith("._"):
                continue
            if nome_do_arquivo.lower().endswith(".csv"):
                caminho_completo = os.path.join(pasta_atual, nome_do_arquivo)
                arquivos_encontrados.append(caminho_completo)
    return sorted(arquivos_encontrados)
 
 
def criar_tabelas(cursor, caminho_schema_sql):
    """Executa o schema.sql inteiro para garantir que as tabelas existem."""
    with open(caminho_schema_sql, "r", encoding="utf-8") as arquivo:
        comandos_sql = arquivo.read()
    cursor.execute(comandos_sql)
 
 
def carregar_csv_na_tabela(cursor, caminho_csv, nome_da_tabela):
    """
    Usa o comando COPY do Postgres para inserir o CSV inteiro na tabela,
    sem nenhum tratamento nos dados.
    """
    with open(caminho_csv, "r", encoding="utf-8") as arquivo_csv:
        comando_copy = (
            f"COPY {nome_da_tabela} FROM STDIN WITH (FORMAT csv, HEADER true)"
        )
        cursor.copy_expert(comando_copy, arquivo_csv)
 
 
def limpar_tabela_antes_de_carregar(cursor, nome_da_tabela):
    """
    Apaga os dados que ja estao na tabela antes de carregar de novo.
 
    Isso e necessario porque as tabelas nao tem PRIMARY KEY: sem uma
    chave unica, o Postgres nao tem como saber que uma linha ja existe,
    entao rodar o COPY duas vezes duplicaria todos os dados. O TRUNCATE
    garante que rodar o script varias vezes sempre da o mesmo resultado
    final, em vez de ir somando dado por cima de dado a cada execucao.
    """
    cursor.execute(f"TRUNCATE TABLE {nome_da_tabela}")
 
 
def main():
    if len(sys.argv) < 3:
        print("Uso: python3 load_csv.py <pasta_ou_zip_de_csvs> <caminho_do_schema.sql>")
        print("Exemplo: python3 load_csv.py ../inputs/dados.zip ../outputs/schema.sql")
        sys.exit(1)
 
    caminho_de_entrada = sys.argv[1]
    caminho_schema_sql = sys.argv[2]
 
    pastas_temporarias = []
    pasta_com_csvs = extrair_zip_se_precisar(caminho_de_entrada, pastas_temporarias)
    arquivos_csv = encontrar_arquivos_csv(pasta_com_csvs)
 
    if not arquivos_csv:
        print(f"Nenhum arquivo .csv encontrado em: {caminho_de_entrada}")
        sys.exit(1)
 
    conexao = psycopg2.connect(**DADOS_DE_CONEXAO)
    cursor = conexao.cursor()
 
    try:
        print(f"Criando tabelas a partir de: {caminho_schema_sql}")
        criar_tabelas(cursor, caminho_schema_sql)
 
        for caminho_csv in arquivos_csv:
            nome_do_arquivo = os.path.basename(caminho_csv)
            nome_da_tabela = limpar_nome(os.path.splitext(nome_do_arquivo)[0])
            print(f"Carregando {nome_do_arquivo} -> tabela '{nome_da_tabela}'")
            limpar_tabela_antes_de_carregar(cursor, nome_da_tabela)
            carregar_csv_na_tabela(cursor, caminho_csv, nome_da_tabela)
 
        conexao.commit()
        print(f"\nPronto! {len(arquivos_csv)} arquivo(s) carregado(s) com sucesso.")
 
    except Exception as erro:
        conexao.rollback()
        print(f"\nErro ao carregar dados, nada foi salvo: {erro}")
        raise
 
    finally:
        cursor.close()
        conexao.close()
        for pasta in pastas_temporarias:
            shutil.rmtree(pasta, ignore_errors=True)
 
 
if __name__ == "__main__":
    main()