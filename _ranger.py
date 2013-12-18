"""
The range trading bot would work on price swings in a preset range

IMPORTANT: You have to configure it to what you believe the trading corridor is!
DISCLAIMER: all losses or harm resulting from the use of this code is YOUR SOLE responsibility
2013-12-12 piramida, based on balancer bot by prof7bit
goxtool is property of prof7bit
"""
 
from datetime import datetime
import strategy
import time
 
RANGE_MIN  = 50     # minimum possible price - at this price, we would be all BTC
RANGE_MAX  = 1250    # maximum possible price - at this price, we would be all FIAT
PERCENT_STEP = 2.37  # each level is this much % above the next; add a prime to not hit walls
 
MARKER      = 9      # lowest digit of price to identify bot's own orders
COIN        = 1E8    # number of satoshi per coin, this is a constant.
VERSION     = 1.0    # version of the bot
 
def add_marker(price, marker):
    """encode a marker in the price value to find bot's own orders"""
    return price / 10 * 10 + marker
 
def has_marker(price, marker):
    """return true if the price value has the marker"""
    return (price % 10) == marker
 
def mark_own(price):
    """return the price with our own marker embedded"""
    return add_marker(price, MARKER)
 
def is_own(price):
    """return true if this price has our own marker"""
    return has_marker(price, MARKER)
 
 
 
class Strategy(strategy.Strategy):
    """a range trading bot"""
    _levels = [] # store price levels

    def __init__(self, gox):
        strategy.Strategy.__init__(self, gox)
        self.temp_halt = False
 
    def slot_keypress(self, gox, (key)):
        """a key has been pressed"""
 
        if key == ord("c"):
            # cancel existing orders and suspend trading
            self.debug("canceling all orders")
            self.temp_halt = True
            self.cancel_orders()
 
        if key == ord("p"):
            # create the initial orders and start trading.
            # market order at current price.
            self.debug("adding 6 orders around current price and enabling trading")
            self.temp_halt = False
            self.place_all_orders()
 
        if key == ord("i"):
            # print some information into the log file about
            # current trading level
            try:
                level = self.closest_level()
            except IndexError:
                level = 0
            self.debug("Closest level: %f [%d]" % (
                gox.quote2float(self.levels[level]), level))
#            self.debug([self.gox.quote2float(x) for x in self.levels])
 

    def cancel_orders(self):
        """cancel all trading orders, we identify
        them through the marker in the price value"""
        must_cancel = []
        for order in self.gox.orderbook.owns:
            if is_own(order.price):
                must_cancel.append(order)
 
        for order in must_cancel:
            self.gox.cancel(order.oid)
 
    @property
    def price_now(self):
        if self.gox.orderbook.bid == 0 or self.gox.orderbook.ask == 0:
            return 0
        return (self.gox.orderbook.bid + self.gox.orderbook.ask) / 2

    @property
    def total_fiat_now(self):
       """ total fiat at curr market price """
       fiat = self.gox.quote2float(self.gox.wallet[self.gox.curr_quote])
       btc = self.gox.base2float(self.gox.wallet[self.gox.curr_base])
       price = self.gox.quote2float(self.price_now)

       return fiat + btc * price

    @property
    def levels(self):
       """ list of prices where we would trade """
       if not self._levels:
           self._levels = []
           val = self.gox.quote2int(RANGE_MIN)
           while val < self.gox.quote2int(RANGE_MAX):
               self._levels.append(mark_own(val))
               val = int(val * (1.0 + PERCENT_STEP / 100.0))
       return self._levels

    def closest_level(self, price=None):
        """ return a trade level closest to the current price """
        if not price:
            price = self.price_now
        if price == 0:
            return -1 # not yet initialized to have correct price
        lvl = self.levels
        return min(range(len(lvl)), key=lambda i: abs(lvl[i]-price))

    def sell_amount(self, price):
        """ how much to sell, in gox btc - our btc divided by number of steps left"""
        idx = self.closest_level()
        ratio = sum([1.0 * price / x for x in self.levels[idx+1:]])
        if ratio == 0:
            return -1
        return int(self.gox.wallet[self.gox.curr_base] / ratio)

    def buy_amount(self, price):
        """ how much to buy, in gox btc - our fiat divided by number of steps left"""
        idx = self.closest_level()
        if idx < 1:
            return -1
        return self.gox.base2int(1.0 * self.gox.wallet[self.gox.curr_quote] / idx / price)

    def place_all_orders(self):
        """ set initial orders at all levels; currently limited to 5 (GOX timelimit) """
        cur_lvl = self.closest_level()
        if cur_lvl == -1:
            return
        start_idx = cur_lvl > 3 and cur_lvl - 3 or 0
        end_idx = (cur_lvl < len(self.levels) - 3) and cur_lvl + 4 or len(self.levels)
        for idx in range(start_idx, end_idx):
            if idx == cur_lvl:
                continue
            if idx > cur_lvl:
                self.place_level_order(idx, True)
            else:
                self.place_level_order(idx, False)

    def place_orders(self):
        """place two orders above and below current level """
        idx = self.closest_level()
        if idx == -1:
            return False
        op = None
        if self.place_level_order(idx + 1, True):
            op = "BOUGHT"
        if self.place_level_order(idx - 1, False):
            op = "SOLD"
        if op:
            self.debug("*** %s at %d (%d) $%d: %s" % (
                op,
                int(self.gox.quote2float(self.levels[idx])),
                idx,
                int(self.total_fiat_now),
                datetime.now()
            ))

    def place_level_order(self, idx, is_sale):
        """ Set an order at the specified level """
        if idx > len(self.levels) or idx < 0:
            self.debug("!!! DONE creating orders since hit the border of range [%s-%s]" % (RANGE_MIN, RANGE_MAX))
            self.temp_halt = True
            return False # done trading
       
        if self.find_level_in_orderbook(idx):
            return False # already set, ignore

        price = self.levels[idx]
        if is_sale:
            amount = self.sell_amount(price)
            if amount < 0.01 * COIN:
                self.debug("*** ERR not enough BTC to sell! Halting trading")
                self.temp_halt = True
                return False
            op = "ask"
            self.gox.sell(price, amount)
        else:
            amount = self.buy_amount(price)
            if amount < 0.01 * COIN:
                self.debug("*** ERR not enough fiat to buy! Halting trading")
                self.temp_halt = True
                return False
            op = "bid"
            self.gox.buy(price, amount)
        self.debug("*** new %s %f at %f (%d)" % (
            op,
            self.gox.base2float(amount),
            self.gox.quote2float(price),
            idx
        ))
        return True
            
    def slot_trade(self, gox, (date, price, volume, typ, own)):
        """a trade message has been receivd"""
        # not interested in other people's trades
        if not own:
            return
 
        # not interested in manually entered (not bot) trades
        if not is_own(price):
            return

        self.check_trades()
 
    def slot_owns_changed(self, orderbook, _dummy):
        """status or amount of own open orders has changed"""
        self.check_trades()
 
    def find_level_in_orderbook(self, level):
        """ returns true if the level is filled with some kind of order """
        if level < 0:
            return True
        price = self.levels[level]
        for order in self.gox.orderbook.owns:
            if order.price == price:
                return True
        # No Matches
        return False
 
    def check_trades(self):
        """find out if we need to place new orders and do it if neccesary"""
 
        # bot temporarily disabled
        if self.temp_halt:
            return
 
        # still waiting for submitted orders,
        # can wait for next signal
        if self.gox.count_submitted:
            return
 
        if not self.find_level_in_orderbook(self.closest_level()):
            # not found our order in the orderbook - try setting the orders!
            self.place_orders()