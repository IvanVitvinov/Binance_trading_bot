from config import API_KEY, API_SECRET, TELEGRAM_TOKEN, CHAT_ID
from binance.client import Client
import time
from tradingview_ta import TA_Handler, Interval
from datetime import datetime

from telegram import Bot
import asyncio
import aiohttp



# Initializing the Binance client using API key and secret
client = Client(api_key=API_KEY, api_secret=API_SECRET)

# Initializing the Telegram bot using the bot token
bot = Bot(token=TELEGRAM_TOKEN)

# Function to get the precision of a symbol
def get_asset_precision(symbol):
    exchange_info = client.futures_exchange_info()
    for asset_info in exchange_info['symbols']:
        if asset_info['symbol'] == symbol:
            return asset_info['quantityPrecision']
    return None

# Function to calculate the quantity of an asset to trade based on a fixed amount in USDT
def get_qnty():
    current_price = float(client.futures_mark_price(symbol=SYMBOL)['markPrice'])
    usdt = 200

    QNTY = usdt / current_price

    QNTY = round(QNTY, 0)

    return QNTY


# Define constants for trading
SYMBOL = 'ANKRUSDT'
INTERVAL = Interval.INTERVAL_1_MINUTE
QNTY = get_qnty()

LEVERAGE = 20
TAKE_PROFIT = 1.012
STOP_LOSS = 0.99

TAKE_PROFIT_FOR_SHORT = 0.988
STOP_LOSS_FOR_SHORT = 1.01


# Function to set the position mode
def set_position_mode(mode):
    try:
        response = client.futures_change_position_mode(dualSidePosition=mode)
        if response['code'] == 200:
            print(f"Position mode changed to: {mode}")
        else:
            print(f"Failed to change position mode: {response}")
    except Exception as e:
        print(f"Error changing position mode: {e}")


# Function to get the USDT balance of the futures account
def get_usdt_balance(client):
    account_info = client.futures_account_balance()
    for balance in account_info:
        if balance["asset"] == "USDT":
            return float(balance["balance"])
    return None


# Function to fetch the current market data
def get_data():
    output = TA_Handler(symbol=SYMBOL,
                            screener='Crypto',
                            exchange='Binance',
                            interval=INTERVAL)

    activiti = output.get_analysis().summary
    return activiti


# Function to cancel all open orders
def cancel_all_open_orders():
    open_orders = client.futures_get_open_orders(symbol=SYMBOL)
    print("Отменяем ордера закрытой позиции!")
    for order in open_orders:
        try:
            client.futures_cancel_order(symbol=SYMBOL, orderId=order['orderId'])
            print(f"Отменен ордер с ID {order['orderId']}")
        except Exception as e:
            print(f"Ошибка при отмене ордера с ID {order['orderId']}: {e}")


# Function to place a new order
def place_order(order_type):
    current_price = float(client.futures_mark_price(symbol=SYMBOL)['markPrice'])
    
    take_profit_price_for_long = round(current_price * TAKE_PROFIT, get_asset_precision)
    stop_loss_price_for_long = round(current_price * STOP_LOSS, get_asset_precision)

    take_profit_price_for_short = round(current_price * TAKE_PROFIT_FOR_SHORT, get_asset_precision)
    stop_loss_price_for_short = round(current_price * STOP_LOSS_FOR_SHORT, get_asset_precision)
    

    if (order_type == 'BUY'):
            # Print data for the order
            print(f'| Entry price: {current_price} |')
            print(f'| Take-profit: {take_profit_price_for_long} |')
            print(f'| Stop-loss: {stop_loss_price_for_long} |')
            print('_____________________')
            
            #Open the order
            order = client.futures_create_order(
                symbol=SYMBOL,
                side=order_type,
                type='MARKET',
                quantity=str(QNTY),
                positionSide='LONG'
            )

            client.futures_create_order(
                symbol=SYMBOL,
                side='SELL',
                type='STOP_MARKET',
                quantity=str(QNTY),
                stopPrice=str(stop_loss_price_for_long),
                positionSide='LONG'
            )

            client.futures_create_order(
                symbol=SYMBOL,
                side='SELL',
                type='TAKE_PROFIT_MARKET',
                quantity=str(QNTY),
                stopPrice=str(take_profit_price_for_long),
                positionSide='LONG'
            )

            print(order)

    if (order_type == 'SELL'):
            # Print data for the order
            print(f'| Entry price: {current_price} |')
            print(f'| Take-profit: {take_profit_price_for_short} |')
            print(f'| Stop-loss: {stop_loss_price_for_short} |')
            print('_____________________')
            
            #Open the order
            order = client.futures_create_order(
                symbol=SYMBOL,
                side="SELL",
                type='MARKET',
                quantity=str(QNTY),
                positionSide='SHORT'
            )

            client.futures_create_order(
                symbol=SYMBOL,
                side='BUY',
                type='STOP_MARKET',
                quantity=str(QNTY),
                stopPrice=str(stop_loss_price_for_short),
                positionSide='SHORT'
            )

            client.futures_create_order(
                symbol=SYMBOL,
                side='BUY',
                type='TAKE_PROFIT_MARKET',
                quantity=str(QNTY),
                stopPrice=str(take_profit_price_for_short),
                positionSide='SHORT'
            )

            print(order)


# Function to close an open position
def close_position(current_position):
    if current_position == 'LONG' or current_position == 'SHORT':
        position_info = client.futures_position_information(symbol=SYMBOL)
        for position in position_info:
            if position['positionSide'] == current_position:
                current_qty = float(position['positionAmt'])

        asset_precision = get_asset_precision(SYMBOL)
        current_qty = round(current_qty, asset_precision)
        current_qty_for_buy = round(current_qty * -1, asset_precision)

        
        str_current_qty_for_buy = str(current_qty_for_buy)

        if current_position == 'LONG':
            print(f'Закрываем ЛОНГ qnty = {current_qty}')
            order = client.futures_create_order(
                symbol=SYMBOL,
                side='SELL',
                type='MARKET',
                positionSide='LONG',
                quantity=current_qty
            )
        
        elif current_position == 'SHORT':
            print(f'Закрываем ШОРТ qnty = {str_current_qty_for_buy}')
            order = client.futures_create_order(
                symbol=SYMBOL,
                side='BUY',
                type='MARKET',
                positionSide='SHORT',
                quantity=str_current_qty_for_buy
            )

def get_current_position():
    # Retrieves the current position information for futures trading
    positions = client.futures_position_information()
    for position in positions:
        if position['symbol'] == SYMBOL:
            if float(position['positionAmt']) > 0:
                return 'LONG'  # If the position amount is greater than 0, it is a long position
            elif float(position['positionAmt']) < 0:
                return 'SHORT'  # If the position amount is less than 0, it is a short position
    return None  # If no position is found, returns None

def get_margin_type():
    # Retrieves the margin type for futures trading account
    account_info = client.futures_account()
    return account_info['multiAssetsMargin']


async def send_telegram_message_async(message):
    # Sends a Telegram message asynchronously
    async with aiohttp.ClientSession() as session:
        api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }
        async with session.post(api_url, data=payload) as response:
            if response.status == 200:
                print("Message sent.")
            else:
                print(f"Error sending message: {await response.text()}")


def send_telegram_message(message):
    # Sends a Telegram message
    loop = asyncio.new_event_loop()  # Creates a new event loop
    loop.run_until_complete(send_telegram_message_async(message))  # Runs the async function in the event loop
    loop.close()  # Closes the event loop


def main():
    # Setting the leverage for the symbol
    client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)

    usdt_balance_start_session = get_usdt_balance(client)
    print(f"Account balance: {usdt_balance_start_session}")
    print('Start script...')
    while True:
        current_position = get_current_position()

        usdt_balance = round(get_usdt_balance(client), 1)
        balance_limit = 20
        profit = 30 - usdt_balance
        inverted_profit = round(profit * -1, 1)

        # Values for the Telegram message
        current_price = float(client.futures_mark_price(symbol=SYMBOL)['markPrice'])
        take_profit_price_for_long = round(current_price * TAKE_PROFIT, 5)
        stop_loss_price_for_long = round(current_price * STOP_LOSS, 5)
        take_profit_price_for_short = round(current_price * TAKE_PROFIT_FOR_SHORT, 5)
        stop_loss_price_for_short = round(current_price * STOP_LOSS_FOR_SHORT, 5)

        data = get_data()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if data['RECOMMENDATION'] in ['STRONG_BUY', 'STRONG_SELL']:
            print(f"{current_time} - {SYMBOL}: {data}")

        if usdt_balance is None or usdt_balance < balance_limit:
            print("Insufficient balance, terminating script.")
            break

    try:
        if current_position is None:
            # Cancel all open orders
            cancel_all_open_orders()

        if (data['RECOMMENDATION'] == 'STRONG_BUY' and (current_position is None or current_position == 'SHORT')):
            print('_________BUY_________')
            print(f'Profit before this trade: {profit}')
            # Cancel all open orders and positions

            try:
                close_position(current_position)
                cancel_all_open_orders()
                place_order('BUY')
                current_position = 'LONG'

            except Exception as e:
                print(f'Error with order: {e}')

            send_telegram_message(f" ⚡️ Position opened! ⚡️ \n(Direction): ⏫ \nAsset: {SYMBOL}\n 🕢 Entry Price: {current_price} \n ✅ Take Profit: {take_profit_price_for_long}\n ❌ Stop Loss: {stop_loss_price_for_long}\nOrder Size: {QNTY} coin\nFutures Balance:  __{usdt_balance}USDT__\nCurrent Profit: __{inverted_profit}USDT__")

        elif (data['RECOMMENDATION'] == 'STRONG_SELL' and (current_position is None or current_position == 'LONG')):
            print('_________SELL_________')
            print(f'Profit before this trade: {profit}')
            # Cancel all open orders

            try:
                close_position(current_position)
                cancel_all_open_orders()
                place_order('SELL')
                current_position = 'SHORT'

            except Exception as e:
                print(f'Error with order: {e}')

            send_telegram_message(f" ⚡️ Position opened! ⚡️ \n(Direction): ⏬ \nAsset: {SYMBOL}\n 🕢 Entry Price: {current_price} \n ✅ Take Profit: {take_profit_price_for_short}\n ❌ Stop Loss: {stop_loss_price_for_short} \nOrder Size: {QNTY} coin\nFutures Balance: __{usdt_balance}USDT__\nCurrent Profit: __{inverted_profit}USDT__")

    except Exception as e:
        print(f"Error placing order: {e}")

    time.sleep(60)


if __name__ == '__main__':
    main()