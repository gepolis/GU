import requests
import time

TONCENTER_API_URL = "https://toncenter.com/api/v2/get_transactions"
ADDRESS = "UQAbDP9z-J-M642XjS5Wtzlyva1JQzITM7kyDt-yLyzjJncr"  # Твой TON-адрес
AMOUNT_TON = 0.01  # Сколько пользователь должен перевести

def get_transactions(address):
    params = {
        "address": address,
        "limit": 5
    }
    response = requests.get(TONCENTER_API_URL, params=params)
    data = response.json()
    return data.get("result", [])

def check_payment(transactions, min_amount):
    for tx in transactions:
        if tx["in_msg"]["value"]:
            value_ton = int(tx["in_msg"]["value"]) / 1e9  # из nanotons в TON
            if value_ton >= min_amount:
                return True, value_ton
    return False, 0

# Проверка цикла
while True:
    txs = get_transactions(ADDRESS)
    paid, amount = check_payment(txs, AMOUNT_TON)
    if paid:
        print(f"✅ Оплата получена: {amount} TON")
        break
    else:
        print("⏳ Ожидание оплаты...")
        time.sleep(10)
