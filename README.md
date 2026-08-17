# Indicium Lighthouse — LH Nautical

Projeto desenvolvido como parte do desafio técnico da **Indicium**, utilizando a base de dados fictícia da **LH Nautical**.

O projeto foi estruturado para cobrir o fluxo completo de análise: ingestão dos dados, exploração, consultas analíticas, previsão de demanda, recomendação de produtos, geração de schema e comunicação dos resultados por meio de um dashboard em Streamlit.

---

## Sumário

- [1. Objetivo](#1-objetivo)
- [2. Arquitetura do projeto](#2-arquitetura-do-projeto)
- [3. Estrutura de diretórios](#3-estrutura-de-diretórios)
- [4. Tecnologias utilizadas](#4-tecnologias-utilizadas)
- [5. Fluxo do projeto](#5-fluxo-do-projeto)
- [6. Ingestão dos dados](#6-ingestão-dos-dados)
- [7. Schema do banco](#7-schema-do-banco)
- [8. Respostas do desafio](#8-respostas-do-desafio)
- [9. Previsão de demanda](#9-previsão-de-demanda)
- [10. Sistema de recomendação](#10-sistema-de-recomendação)
- [11. Dashboard](#11-dashboard)
- [12. Materiais complementares](#12-materiais-complementares)
- [13. Como executar o projeto](#13-como-executar-o-projeto)
- [14. Qualidade e decisões analíticas](#14-qualidade-e-decisões-analíticas)
- [15. Possíveis evoluções](#15-possíveis-evoluções)

---

# 1. Objetivo

O objetivo deste projeto é analisar os dados comerciais da **LH Nautical** e responder às perguntas propostas no desafio técnico, além de apresentar uma visão analítica complementar sobre o negócio.

A solução foi organizada pensando em um cenário próximo ao encontrado em um ambiente real de dados:

```text
Dados brutos
    │
    ▼
Ingestão / Load
    │
    ▼
PostgreSQL
    │
    ├──────────────► Consultas analíticas
    │
    ├──────────────► Previsão de demanda
    │
    ├──────────────► Recomendação de produtos
    │
    └──────────────► Dashboard
```

Além das respostas objetivas, o projeto busca demonstrar capacidade de:

- trabalhar com dados relacionais;
- realizar análise exploratória;
- construir consultas SQL;
- tratar problemas de qualidade e consistência;
- aplicar conceitos estatísticos;
- criar um baseline de previsão;
- desenvolver uma recomendação baseada em comportamento de compra;
- comunicar resultados para públicos técnicos e não técnicos.

---

# 2. Arquitetura do projeto

A arquitetura foi mantida simples e modular para facilitar a reprodução do desafio.

```text
                    ┌─────────────────────┐
                    │  CSV / Dados brutos │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Load/         │
                    │     load_csv.py     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     PostgreSQL      │
                    │     LH Nautical     │
                    └──────────┬──────────┘
                               │
               ┌───────────────┼────────────────┐
               │               │                │
               ▼               ▼                ▼
        ┌────────────┐  ┌────────────┐  ┌──────────────┐
        │  Answers   │  │  Predict   │  │   Recomend   │
        │ SQL / EDA  │  │ Forecast   │  │ Similaridade │
        └─────┬──────┘  └─────┬──────┘  └──────┬───────┘
              │               │                │
              └───────────────┼────────────────┘
                              ▼
                    ┌─────────────────────┐
                    │     Dashboard       │
                    │      Streamlit      │
                    └─────────────────────┘
```

---

# 3. Estrutura de diretórios

```text
INDICIUM_LIGHTHOUSE/
│
├── answers/
│   ├── 1.1.sql
│   ├── 2.1.py
│   ├── 2.2.sql
│   ├── 3.1.py
│   ├── 4.1.sql
│   ├── 5.1.sql
│   ├── 6.1.py
│   ├── 7.1.py
│   └── dashboard.py
│
├── inputs/
│   └── 1-lh_nautical_csv.zip
│
├── Load/
│   └── load_csv.py
│
├── outputs/
│   └── schema.sql
│
├── predict/
│   └── predict.py
│
├── Recomend/
│   └── recomend.py
│
├── schema_question/
│   └── generate_schema.py
│
├── README.md
└── requirements.txt
```

## Responsabilidade de cada diretório

### `answers/`

Contém as soluções das perguntas do desafio.

Os arquivos foram mantidos separados para facilitar a identificação entre as questões SQL e Python.

| Arquivo | Responsabilidade |
|---|---|
| `1.1.sql` | Resposta SQL da questão 1.1 |
| `2.1.py` | Análise/resposta Python da questão 2.1 |
| `2.2.sql` | Resposta SQL da questão 2.2 |
| `3.1.py` | Análise/resposta Python da questão 3.1 |
| `4.1.sql` | Resposta SQL da questão 4.1 |
| `5.1.sql` | Resposta SQL da questão 5.1 |
| `6.1.py` | Análise/resposta Python da questão 6.1 |
| `7.1.py` | Análise/resposta Python da questão 7.1 |
| `dashboard.py` | Dashboard analítico desenvolvido em Streamlit |

### `inputs/`

Contém os dados de entrada fornecidos no desafio.

```text
inputs/
└── 1-lh_nautical_csv.zip
```

O ZIP contém as tabelas CSV utilizadas na análise.

### `Load/`

Responsável pela ingestão dos arquivos CSV para o banco de dados.

```text
Load/
└── load_csv.py
```

O script realiza a leitura dos dados e a carga no PostgreSQL.

### `outputs/`

Contém artefatos gerados durante o processo.

```text
outputs/
└── schema.sql
```

O `schema.sql` representa a estrutura utilizada para as tabelas do projeto.

### `predict/`

Contém a análise relacionada à previsão de demanda.

```text
predict/
└── predict.py
```

A solução utiliza um baseline de média móvel para estimar a demanda futura e posteriormente avaliar seu desempenho em um período de teste.

### `Recomend/`

Contém a solução de recomendação de produtos.

```text
Recomend/
└── recomend.py
```

A recomendação utiliza o comportamento de compra dos clientes para calcular afinidade entre produtos.

### `schema_question/`

Responsável pela geração/apoio à construção do schema utilizado no desafio.

```text
schema_question/
└── generate_schema.py
```

---

# 4. Tecnologias utilizadas

## Linguagens

- **Python**
- **SQL**

## Banco de dados

- **PostgreSQL**

## Python

- **Pandas** — manipulação e análise dos dados
- **NumPy** — cálculos numéricos
- **Psycopg2** — conexão com PostgreSQL
- **Streamlit** — dashboard interativo

## Ferramentas

- Visual Studio Code
- PostgreSQL
- Jupyter Notebook
- Git/GitHub

---

# 5. Fluxo do projeto

O fluxo recomendado para reprodução do projeto é:

```text
1. Preparar ambiente
        ↓
2. Instalar dependências
        ↓
3. Criar banco PostgreSQL
        ↓
4. Gerar/aplicar schema
        ↓
5. Carregar CSVs
        ↓
6. Executar respostas do desafio
        ↓
7. Executar previsão
        ↓
8. Executar recomendação
        ↓
9. Abrir dashboard
```

---

# 6. Ingestão dos dados

Os dados fornecidos pelo desafio estão disponíveis em:

```text
inputs/1-lh_nautical_csv.zip
```

A ingestão é realizada pelo script:

```text
Load/load_csv.py
```

A ideia é centralizar a carga dos arquivos no PostgreSQL para que as consultas SQL possam trabalhar sobre uma estrutura relacional.

O processo pode ser representado como:

```text
CSV
 │
 ├── customers
 ├── orders
 ├── order_items
 ├── products
 ├── product_variants
 ├── categories
 └── demais tabelas
       │
       ▼
   PostgreSQL
```

Essa abordagem permite separar claramente:

- **dados brutos**;
- **camada de armazenamento**;
- **lógica analítica**;
- **apresentação dos resultados**.

---

# 7. Schema do banco

O schema utilizado no projeto está disponível em:

```text
outputs/schema.sql
```

A estrutura relacional permite trabalhar principalmente com entidades como:

- clientes;
- pedidos;
- itens de pedidos;
- produtos;
- variantes;
- categorias;
- demais dimensões relacionadas ao catálogo e às vendas.

Uma das principais relações analíticas é:

```text
customer
    │
    └── orders
            │
            └── order_items
                    │
                    └── product_variants
                            │
                            └── products
                                    │
                                    └── categories
```

Essa estrutura permite análises de:

- faturamento;
- ticket médio;
- frequência de compra;
- mix de produtos;
- categorias;
- comportamento dos clientes;
- recomendação de produtos;
- demanda ao longo do tempo.

---

# 8. Respostas do desafio

As respostas foram organizadas em `answers/` de acordo com a numeração do desafio.

## SQL

As questões SQL estão representadas pelos arquivos:

```text
answers/
├── 1.1.sql
├── 2.2.sql
├── 4.1.sql
└── 5.1.sql
```

## Python

As questões que demandam análise e/ou processamento em Python estão em:

```text
answers/
├── 2.1.py
├── 3.1.py
├── 6.1.py
└── 7.1.py
```

A separação entre SQL e Python foi mantida para deixar explícita a ferramenta utilizada em cada etapa.

---

# 9. Previsão de demanda

A previsão foi desenvolvida em:

```text
predict/predict.py
```

O produto analisado é:

**Bússola de Bordo 702**

Foi utilizado um baseline baseado na **média móvel dos três meses anteriores**.

A lógica pode ser representada por:

```text
Forecast(t) =
    média(
        demanda(t-1),
        demanda(t-2),
        demanda(t-3)
    )
```

## Avaliação

O modelo foi avaliado sobre um período de teste, comparando:

```text
Demanda real
     ×
Previsão
```

Uma métrica utilizada foi o **MAE — Mean Absolute Error**:

```text
MAE = média(|real - previsão|)
```

O resultado mostrou que o baseline possui erro relevante para ser utilizado isoladamente em decisões de compra.

### Limitações identificadas

A média móvel simples:

- não captura adequadamente tendência;
- não captura sazonalidade;
- não considera estoque;
- não diferencia baixa demanda de ruptura;
- utiliza apenas o histórico observado.

Portanto, a solução deve ser interpretada como um **baseline**, e não como um modelo definitivo de forecasting.

### Evolução recomendada

Em um cenário produtivo, seria interessante avaliar:

- modelos estatísticos de séries temporais;
- regressão com variáveis externas;
- modelos de gradient boosting;
- sazonalidade;
- calendário comercial;
- preço;
- promoções;
- disponibilidade de estoque.

---

# 10. Sistema de recomendação

A recomendação está em:

```text
Recomend/recomend.py
```

O produto utilizado como referência é:

**Motor de Popa 1949**

A abordagem utiliza uma matriz:

```text
             Produto A  Produto B  Produto C
Cliente 1        1          1          0
Cliente 2        1          0          1
Cliente 3        0          1          1
...
```

Onde:

```text
1 = cliente comprou o produto
0 = cliente não comprou
```

A partir dessa matriz, é calculada a **similaridade de cosseno** entre os produtos.

A ideia é encontrar produtos comprados por conjuntos de clientes semelhantes.

## Interpretação

A lógica responde aproximadamente:

> "Clientes que compraram este produto também demonstraram comportamento de compra semelhante em quais outros produtos?"

Isso permite construir uma estratégia de **cross-sell**.

## Limitações

A similaridade de cosseno é um baseline adequado para o problema, porém não considera:

- recência;
- frequência;
- valor da compra;
- margem;
- disponibilidade;
- sazonalidade;
- categoria;
- preço;
- contexto da compra.

Uma versão de produção poderia combinar esses fatores em um ranking híbrido.

---

# 11. Dashboard

O dashboard foi desenvolvido em:

```text
answers/dashboard.py
```

A aplicação utiliza **Streamlit** e foi construída para funcionar diretamente com o ZIP dos CSVs.

## Visões disponíveis

### Visão executiva

Apresenta os principais KPIs:

- faturamento;
- pedidos;
- ticket médio;
- clientes;
- unidades;
- margem estimada.

Também apresenta:

- evolução do faturamento;
- faturamento por canal;
- principais categorias.

---

### Vendas

Permite analisar:

- pedidos por canal;
- ticket médio por canal;
- faturamento diário;
- comportamento do POS;
- vendas por dia da semana.

---

### Clientes

Apresenta:

- ranking de clientes;
- faturamento por cliente;
- frequência;
- ticket médio;
- quantidade de categorias distintas compradas;
- clientes que atendem ao critério de fidelidade definido no desafio.

---

### Produtos

Apresenta:

- produtos com maior faturamento;
- produtos com maior volume;
- margem estimada;
- participação dos produtos no resultado.

A margem utilizada no dashboard é uma estimativa baseada em:

```text
Margem = Receita - Custo estimado
```

---

### Previsão

Reproduz a análise da:

**Bússola de Bordo 702**

Inclui:

- histórico mensal;
- baseline de média móvel de 3 meses;
- comparação real × previsto;
- MAE;
- erro percentual.

---

### Recomendação

Reproduz a análise do:

**Motor de Popa 1949**

Apresenta:

- matriz cliente × produto;
- similaridade de cosseno;
- ranking dos produtos recomendados.

---

### Qualidade dos dados

Inclui verificações relacionadas a:

- quantidade de registros;
- quantidade de colunas;
- células nulas;
- valores negativos;
- extremos da variável `total`;
- inconsistências conhecidas.

---

# 12. Materiais complementares

Além do código principal, foram produzidos materiais para facilitar a comunicação da análise.

## Notebook

O notebook documenta o raciocínio analítico passo a passo, incluindo:

- carregamento;
- EDA;
- análise comercial;
- clientes;
- calendário;
- forecasting;
- recomendação;
- qualidade dos dados.

## Relatório

O relatório executivo resume:

- principais KPIs;
- principais descobertas;
- metodologia;
- limitações;
- recomendações;
- próximos passos.

A intenção é que o material possa ser consumido mesmo por uma pessoa que não queira executar o código.

---

# 13. Como executar o projeto

## 13.1. Pré-requisitos

Instale:

- Python 3.10+
- PostgreSQL
- pip

Recomenda-se utilizar um ambiente virtual.

---

## 13.2. Criar ambiente virtual

No Windows:

```bash
python -m venv .venv
```

Ativar:

```bash
.venv\Scripts\activate
```

No PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 13.3. Instalar dependências

```bash
pip install -r requirements.txt
```

---

## 13.4. Preparar o PostgreSQL

Crie um banco de dados para o projeto.

Depois, utilize o schema disponível em:

```text
outputs/schema.sql
```

---

## 13.5. Carregar os dados

Execute:

```bash
python Load/load_csv.py
```

O script realiza a ingestão dos CSVs disponíveis em:

```text
inputs/1-lh_nautical_csv.zip
```

---

# 13.6. Executar as análises

As respostas individuais podem ser executadas a partir da pasta:

```text
answers/
```

Exemplos:

```bash
python answers/2.1.py
```

```bash
python answers/3.1.py
```

```bash
python answers/6.1.py
```

```bash
python answers/7.1.py
```

As consultas SQL podem ser executadas diretamente no PostgreSQL ou na ferramenta de administração utilizada.

---

# 13.7. Executar o dashboard

A partir da raiz do projeto:

```bash
streamlit run answers/dashboard.py
```

O Streamlit exibirá no terminal o endereço local da aplicação.

Normalmente:

```text
http://localhost:8501
```

O dashboard possui um upload para o arquivo:

```text
inputs/1-lh_nautical_csv.zip
```

Dessa forma, a visualização pode ser executada independentemente da conexão com o PostgreSQL.

---

# 14. Qualidade e decisões analíticas

Durante a análise foram observados alguns pontos relevantes.

## Outliers em `total`

Os maiores valores de `total` apresentam uma queda relativamente gradual entre os pedidos de maior valor.

Não foi observado um salto isolado suficientemente forte para caracterizar, por si só, um erro evidente de carga ou digitação.

Por isso, os valores extremos foram tratados como potenciais pedidos legítimos e não simplesmente removidos.

---

## Produtos com nomes duplicados

Foi identificada uma duplicidade de nome para:

**Bússola de Bordo 702**

Esse tipo de situação é importante porque o nome comercial não deve necessariamente ser tratado como identificador único.

Para a análise de previsão, foi necessário distinguir os registros e evitar a mistura de possíveis SKUs diferentes.

Em um ambiente produtivo, a recomendação seria utilizar uma chave de produto/variante confiável em vez do nome.

---

## Previsão e estoque

Um ponto importante da análise é que:

```text
venda observada ≠ demanda real
```

Se um produto estiver sem estoque, suas vendas podem ser zero mesmo existindo demanda.

Portanto, uma previsão de demanda mais robusta deveria considerar:

```text
Demanda observada
        +
Disponibilidade de estoque
        +
Preço
        +
Promoções
        +
Calendário
```

---

## Recomendação

A similaridade de cosseno fornece uma boa primeira abordagem para encontrar produtos com comportamento de compra semelhante.

Entretanto, uma recomendação comercial real deveria considerar também:

- margem;
- estoque;
- recência;
- frequência;
- valor;
- categoria;
- preço.

---

# 15. Possíveis evoluções

Caso o projeto fosse evoluído para um ambiente produtivo, os próximos passos seriam:

### Engenharia de dados

- separar camadas raw/staging/mart;
- criar pipelines automatizados;
- adicionar testes de qualidade;
- implementar logging;
- criar monitoramento;
- adicionar CI/CD.

### Analytics

- criar uma camada dimensional;
- construir uma dimensão calendário;
- criar métricas padronizadas;
- desenvolver análises de cohort;
- calcular LTV;
- segmentar clientes;
- analisar churn.

### Forecasting

Evoluir o baseline para modelos que considerem:

- tendência;
- sazonalidade;
- estoque;
- preço;
- promoções;
- calendário.

### Recomendação

Evoluir de similaridade simples para um sistema híbrido utilizando:

```text
Collaborative Filtering
        +
Popularidade
        +
Recência
        +
Margem
        +
Disponibilidade
```

### Dashboard

Adicionar:

- drill-down;
- segmentação por cliente;
- análise de cohort;
- alertas;
- metas;
- comparação com período anterior;
- análise de margem;
- monitoramento de estoque.

---

# Conclusão

O projeto foi desenvolvido com o objetivo de responder ao desafio técnico e, ao mesmo tempo, demonstrar uma visão de ponta a ponta sobre um problema de dados.

A solução parte dos dados brutos, passa pela ingestão e modelagem relacional, aplica SQL e Python para responder às perguntas analíticas, explora previsão e recomendação e termina em uma camada de visualização construída em Streamlit.

Além dos resultados, foram documentadas as principais limitações e oportunidades de evolução, com foco em transformar os baselines desenvolvidos durante o desafio em soluções mais robustas para um cenário de produção.

---

## Autor

Projeto desenvolvido para o desafio técnico da **Indicium**.

**Stack principal:** Python · SQL · PostgreSQL · Pandas · NumPy · Streamlit
