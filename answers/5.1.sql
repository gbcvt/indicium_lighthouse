WITH vendas_lojas_fisicas AS (
    SELECT
        placed_at::date AS data_venda,
        total
    FROM orders
    WHERE channel = 'pos'
),
dimensao_datas AS (
    SELECT
        generate_series(
            (SELECT MIN(data_venda) FROM vendas_lojas_fisicas),
            (SELECT MAX(data_venda) FROM vendas_lojas_fisicas),
            interval '1 day'
        )::date AS data_calendario
),
vendas_por_dia AS (
    SELECT
        data_venda,
        SUM(total) AS venda_diaria
    FROM vendas_lojas_fisicas
    GROUP BY data_venda
),
calendario_com_vendas AS (
    SELECT
        d.data_calendario,
        COALESCE(v.venda_diaria, 0) AS venda_diaria,
        EXTRACT(DOW FROM d.data_calendario) AS dia_semana_numero,
        CASE EXTRACT(DOW FROM d.data_calendario)
            WHEN 0 THEN 'Domingo'
            WHEN 1 THEN 'Segunda-feira'
            WHEN 2 THEN 'Terça-feira'
            WHEN 3 THEN 'Quarta-feira'
            WHEN 4 THEN 'Quinta-feira'
            WHEN 5 THEN 'Sexta-feira'
            WHEN 6 THEN 'Sábado'
        END AS dia_semana
    FROM dimensao_datas d
    LEFT JOIN vendas_por_dia v ON v.data_venda = d.data_calendario
)
-- Resultado final: media de vendas por dia da semana, considerando
-- todos os dias do calendario (inclusive os sem venda). Ordenado da
-- PIOR media para a melhor, para responder direto a pergunta do
-- Sr. Almir.
SELECT
    dia_semana,
    ROUND(AVG(venda_diaria), 2) AS media_vendas,
    COUNT(*) AS dias_no_periodo,
    SUM(CASE WHEN venda_diaria = 0 THEN 1 ELSE 0 END) AS dias_sem_venda
FROM calendario_com_vendas
GROUP BY dia_semana, dia_semana_numero
ORDER BY media_vendas ASC;