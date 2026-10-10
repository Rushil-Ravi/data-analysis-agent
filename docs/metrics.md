# Metric Definitions (project-specific, simplified)

Data: Olist Brazilian e-commerce dataset (public). Tables: orders, order_items, order_payments, order_reviews, customers, products, sellers, product_category_name_translation.

## Valid order
Any row in orders where order_status is not 'canceled' and not 'unavailable'.

## Revenue
Sum of price (excluding freight_value) in order_items, for orders with order_status = 'delivered'.

## Average order value (AOV)
Revenue divided by the number of distinct delivered orders.

## Delivery time
Days between order_purchase_timestamp and order_delivered_customer_date, for delivered orders only.

## Late delivery
A delivered order where order_delivered_customer_date is later than order_estimated_delivery_date. Late delivery rate = late orders / delivered orders.

## Customer
Use customer_unique_id from the customers table to identify a person. customer_id in orders is created per order, so it cannot be used to count repeat customers.

## Repeat customer
A customer_unique_id with more than one valid order.

## Active customer
A customer_unique_id with at least one valid order in the 90 days before the most recent order_purchase_timestamp in the dataset.

## Review score and unhappy customers
review_score ranges from 1 to 5. Satisfaction = average review_score. An unhappy customer review is a score of 1 or 2.

## Product category
Category names are in Portuguese in products. Join product_category_name_translation to get product_category_name_english.

## Joining tables
orders to customers on customer_id; order_items to orders on order_id; order_items to products on product_id; order_reviews to orders on order_id.
