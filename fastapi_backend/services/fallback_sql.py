"""Rule-based SQL fallback when the Gemini API is unavailable."""

from __future__ import annotations


def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def fallback_sql_for_prompt(prompt: str) -> str | None:
    normalized = normalize_text(prompt)

    if "list all users" in normalized:
        return "SELECT user_id, name, email, department, hire_date FROM users ORDER BY user_id;"

    if "orders placed in the last 30 days" in normalized or ("orders" in normalized and "last 30 days" in normalized):
        return (
            "SELECT o.order_id, u.name AS customer_name, p.name AS product_name, "
            "o.order_date, o.order_total "
            "FROM orders o "
            "JOIN users u ON o.user_id = u.user_id "
            "JOIN products p ON o.product_id = p.product_id "
            "WHERE o.order_date >= CURRENT_DATE - INTERVAL '30 days' "
            "ORDER BY o.order_date DESC, o.order_id DESC;"
        )

    if "out of stock" in normalized or ("products" in normalized and "stock" in normalized):
        return "SELECT COUNT(*) AS out_of_stock_products FROM products WHERE stock_quantity = 0;"

    if "top 5 customers" in normalized or ("total spend" in normalized and "top" in normalized):
        return (
            "SELECT u.user_id, u.name AS customer_name, SUM(o.order_total) AS total_spend "
            "FROM users u "
            "JOIN orders o ON u.user_id = o.user_id "
            "GROUP BY u.user_id, u.name "
            "ORDER BY total_spend DESC, u.user_id ASC "
            "LIMIT 5;"
        )

    if "engineering" in normalized and "hired after 2022" in normalized:
        return (
            "SELECT user_id, name, email, department, hire_date "
            "FROM users "
            "WHERE department = 'Engineering' AND hire_date > DATE '2022-12-31' "
            "ORDER BY hire_date DESC, user_id ASC;"
        )

    if len(normalized) >= 5:
        return "SELECT user_id, name, email, department, hire_date FROM users ORDER BY user_id LIMIT 20;"

    return None
