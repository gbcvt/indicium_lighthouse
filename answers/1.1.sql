select 
count(*) as count_rows,
min(created_at) as min_data,
max(created_at) as max_data,
min(total) as min_total,
max(total) as max_total,
avg(total) as avg_total
from orders