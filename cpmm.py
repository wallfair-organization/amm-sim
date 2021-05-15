#
# Constant Price Market Making Simulator
#
# simulate different liquidity provision and trading strategies
#


# @Marcin: Let's focus on binary outcome with 50:50 distribution initial

import random 
#import numpy #sample from different distributions // uniform, bernoulli, X^2


#global state parameters
lp_token = 0
lp_yes = 0
lp_no = 0
buy_price_yes = 0
sell_price_yes = 0
buy_price_no = 0
sell_price_no = 0
history = [("activity", "type", "amount", "token_buy_price_old", "token_buy_price_new", "returned tokens", "lp_yes", "lp_no", "lp_token")]

def create_event(liquidity):
	add_liquidity(liquidity)

def add_liquidity(amount):
	global history, lp_token, lp_yes, lp_no, buy_price_yes, sell_price_yes, buy_price_no, sell_price_no

	lp_token = lp_token + amount
	lp_yes = lp_yes + amount
	lp_no = lp_no + amount
	buy_price_yes_old = buy_price_yes
	buy_price_yes = (buy_price_yes + amount) /  (lp_yes + lp_no)
	sell_price_yes = (sell_price_yes + amount) /  (lp_yes + lp_no)
	buy_price_no = (buy_price_no + amount) /  (lp_yes + lp_no)
	sell_price_no = (sell_price_no + amount) / (lp_yes + lp_no)
	
	entry = ("add", "liquidity", amount, buy_price_yes_old,  buy_price_yes, "0", lp_yes, lp_no, lp_token)
	history.append(entry)



# def remove_liquidity(amount):
	

def buy_token(type, amount): #yes=1 | no = 0
	
	global history, lp_yes, lp_no, lp_token, buy_price_yes, buy_price_no

	lp_token = lp_token + amount

	if type:
		
		lp_yes += amount
		lp_no += amount
		x = (lp_yes * lp_no)/ (lp_no * amount) - lp_yes
		lp_yes += x
		tokens_return = amount - x
		buy_price_yes_old = buy_price_yes
		buy_price_yes = amount / (amount - x)
		
		entry = ("buy", "yes", amount, buy_price_yes_old,  buy_price_yes, tokens_return, lp_yes, lp_no, lp_token)
		history.append(entry)

	else:
		lp_yes += amount
		lp_no += amount
		x = (lp_yes * lp_no)/ (lp_yes * amount) - lp_no
		lp_no += x
		tokens_return = amount - x
		buy_price_no_old = buy_price_no
		buy_price_no = amount / (amount - x)
		
		entry = ("buy", "no", amount, buy_price_no_old,  buy_price_no, tokens_return, lp_yes, lp_no, lp_token)
		history.append(entry)


		
# def sell_token(type, amount):

# def get_buy_price_yes():

# def get_sell_price_yes():


def main():
	
	#experiment 1
	
	
	n = 100 # n= 100 trades
	
	create_event(100) # amount=100 // intial liquidity, fixed
	
	for i in range(n):
		b = random.getrandbits(1) # yes/no uniformly sampled
		amount = random.randint(1,50) # buy range [1,50], uniformly sampled 
		buy_token(b, amount)

	print(history)

if __name__ == "__main__":
    main()
