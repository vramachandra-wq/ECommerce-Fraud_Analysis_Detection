-- Align product categories with catalog taxonomy
UPDATE master.products SET category = 'Electronics'
WHERE product_id IN ('PROD-9905', 'PROD-9907', 'PROD-9959', 'PROD-9913');
