WITH faturamento_por_cliente AS (
    SELECT
        customer_id,
        SUM(total) AS faturamento_total,
        COUNT(id) AS frequencia
    FROM orders
    GROUP BY customer_id
),
diversidade_por_cliente AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT p.category_id) AS diversidade_categorias
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p ON p.id = pv.product_id
    GROUP BY o.customer_id
)
SELECT
    f.customer_id,
    f.faturamento_total,
    f.frequencia,
    ROUND(f.faturamento_total / f.frequencia, 2) AS ticket_medio,
    d.diversidade_categorias
FROM faturamento_por_cliente f
JOIN diversidade_por_cliente d ON d.customer_id = f.customer_id
WHERE d.diversidade_categorias >= 13
ORDER BY ticket_medio DESC, f.customer_id ASC
LIMIT 10; 