# Metric Definitions (project-specific, simplified)

Data: Olist Brazilian e-commerce dataset (public). Tables: orders, order\_items, order\_payments, order\_reviews, customers, products, sellers, product\_category\_name\_translation.

## Valid order

Any row in orders where order\_status is not 'canceled' and not 'unavailable'.

## Revenue

Sum of price (excluding freight\_value) in order\_items, for orders with order\_status = 'delivered'.

## Average order value (AOV)

Revenue divided by the number of distinct delivered orders.

## Delivery time

Days between order\_purchase\_timestamp and order\_delivered\_customer\_date, for delivered orders only.

## Late delivery

A delivered order where order\_delivered\_customer\_date is later than order\_estimated\_delivery\_date. Late delivery rate = late orders / delivered orders.

## Customer

Use customer\_unique\_id from the customers table to identify a person. customer\_id in orders is created per order, so it cannot be used to count repeat customers.

## Repeat customer

A customer\_unique\_id with more than one valid order.

## Active customer

A customer\_unique\_id with at least one valid order in the 90 days before the most recent order\_purchase\_timestamp in the dataset.

## Review score and unhappy customers

review\_score ranges from 1 to 5. Satisfaction = average review\_score. An unhappy customer review is a score of 1 or 2.

## Product category

Category names are in Portuguese in products. Join product\_category\_name\_translation to get product\_category\_name\_english.

## Joining tables

orders to customers on customer\_id; order\_items to orders on order\_id; order\_items to products on product\_id; order\_reviews to orders on order\_id.



\## Monthly revenue

Group revenue by month of order\_purchase\_timestamp, using strftime('%Y-%m', order\_purchase\_timestamp). Only delivered orders count.



\## Data coverage

Delivered-order revenue by purchase month runs from September 2016 to August 2018. Months in 2016 are very small, and November 2016 has no delivered orders. Treat the first and last months as partial.



\## Delivered order

An order with order\_status = 'delivered'. Always identify delivered orders by order\_status, never by whether a delivery date exists.



\## Currency

All monetary values (price, freight\_value, payment\_value) are in Brazilian reais (BRL, R$). Never use a dollar sign.



\## Not available in this dataset

There is no product cost, supplier cost, or profit data. Profit, margin, and COGS cannot be computed. Freight\_value is a shipping fee, not a cost. There is also no data on returns, ad spend, inventory, or customer demographics beyond city and state.







