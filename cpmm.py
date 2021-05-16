#
# Constant Price Market Making Simulator
#
# simulate different liquidity provision and trading strategies
#


# @Marcin: Let's focus on binary outcome with 50:50 distribution initial

import random

import csv
from numpy import apply_along_axis
import pandas as pd
#import numpy #sample from different distributions // uniform, bernoulli, X^2

# TODO: switch to decimal type and control quantization. numeric errors will kill us quickly


#global state parameters
initial_liquidity = 0
lp_token = 0
lp_yes = 0
lp_no = 0
buy_price_yes = 0
sell_price_yes = 0
buy_price_no = 0
sell_price_no = 0
history = []

def create_event(liquidity):
	global initial_liquidity

	initial_liquidity = liquidity
	add_liquidity(liquidity)

def add_liquidity(amount):
	global history, lp_token, lp_yes, lp_no, buy_price_yes, sell_price_yes, buy_price_no, sell_price_no

	lp_token = lp_token + amount
	lp_yes = lp_yes + amount
	lp_no = lp_no + amount
	# TODO: not sure those formulas are correct....
	buy_price_yes_old = buy_price_yes
	buy_price_yes = (buy_price_yes + amount) /  (lp_yes + lp_no)
	sell_price_yes = (sell_price_yes + amount) /  (lp_yes + lp_no)
	buy_price_no = (buy_price_no + amount) /  (lp_yes + lp_no)
	sell_price_no = (sell_price_no + amount) / (lp_yes + lp_no)
	
	entry = ["add", "liquidity", amount, buy_price_yes_old,  buy_price_yes, 0, 0, lp_yes, lp_no, lp_token, 0 ,0]
	history.append(entry)



# def remove_liquidity(amount):
	

def buy_token(type, amount): #yes=1 | no = 0
	global history, lp_yes, lp_no, lp_token, buy_price_yes, buy_price_no, initial_liquidity

	# keep invariant
	k = (lp_yes * lp_no)
	# add liquidity
	lp_token = lp_token + amount

	if type:
		x = k / (lp_no + amount) - lp_yes
		tokens_return = amount - x

		buy_price_yes_old = buy_price_yes
		buy_price_yes = amount / tokens_return
		# calc slippage
		marginal_price_yes = lp_no / (lp_no + lp_yes)
		slippage_yes = (buy_price_yes - marginal_price_yes) / marginal_price_yes
		assert(slippage_yes > 0)

		# remove returned token form the pool, keep all no tokens
		lp_yes += x
		lp_no += amount
		
		entry = ["buy", "yes", amount, buy_price_yes_old,  buy_price_yes, slippage_yes, tokens_return, lp_yes, lp_no, lp_token, 0, 0]
	else:
		x = k / (lp_yes + amount) - lp_no
		tokens_return = amount - x

		buy_price_no_old = buy_price_no
		buy_price_no = amount / tokens_return
		# calc slippage
		marginal_price_no = lp_yes / (lp_no + lp_yes)
		slippage_no = (buy_price_no - marginal_price_no) / marginal_price_no
		assert(slippage_no > 0)

		# remove returned token form the pool, keep all yes tokens
		lp_no += x
		lp_yes += amount

		entry = ["buy", "no", amount, buy_price_no_old,  buy_price_no, slippage_no, tokens_return, lp_yes, lp_no, lp_token, 0, 0]

	# assert invariant, we use float and disregard rounding so must be within e ~ 0
	print(f"invariant {k} {lp_yes * lp_no}")
	assert(abs(k - (lp_yes * lp_no)) < 0.000001)
	
	# calculate impermanent loss for initial LP assuming 50:50 split
	# convert matching yes/no into collateral
	withdraw_token = min(lp_yes, lp_no)
	impermanent_loss = initial_liquidity - withdraw_token
	assert(impermanent_loss >= 0)
	# outstanding yes/no token may be converted at event outcome to reward or immediately traded
	if lp_yes > lp_no:
		outstanding_token = lp_yes - withdraw_token
	else:
		outstanding_token = lp_no - withdraw_token
	
	# impermanent loss at last position in history entry
	entry[-2] = impermanent_loss
	entry[-1] = outstanding_token

	history.append(entry)
		
# def sell_token(type, amount):

# def get_buy_price_yes():

# def get_sell_price_yes():


def main():
	
	#experiment 1
	
	
	n = 100 # n= 100 trades
	
	create_event(100) # amount=100 // intial liquidity, fixed
	
	for i in range(n):
		# TODO: use bernoulli dist to simulate prior diffferent than 50:50
		b = random.getrandbits(1) # yes/no uniformly sampled
		# TODO: sample amounts from some power law distribution to approx. real behavior (or take data from polymarket)
		# TODO: compute slippage and bail off when too large
		amount = random.randint(1,50) # buy range [1,50], uniformly sampled 
		buy_token(b, amount)

	print(history)
	df = pd.DataFrame(data=history, columns=["activity", "type", "amount", "token_buy_price_old", "token_buy_price_new", "slippage", "returned tokens", "lp_yes", "lp_no", "lp_token", "impermanent_loss", "loss_outstanding_tokens"])
	with open("experiment1.csv", "w") as f:
		df.to_csv(f, index=False, quoting=csv.QUOTE_NONNUMERIC)

if __name__ == "__main__":
    main()
