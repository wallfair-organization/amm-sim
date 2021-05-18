#
# Constant Price Market Making Simulator
#
# simulate different liquidity provision and trading strategies
#

from typing import Tuple

import csv
import numpy as np
import pandas as pd
from numpy.random import binomial, default_rng

# TODO: switch to decimal type and control quantization. numeric errors will kill us quickly


class CPMM(object):
	def __init__(self, fee_fraction = 0, fee_to_liquidity_fraction = 0) -> None:
		self.initial_liquidity = 0
		self.lp_token = 0
		self.lp_yes = 0
		self.lp_no = 0
		self.buy_price_yes = 0
		self.sell_price_yes = 0
		self.buy_price_no = 0
		self.sell_price_no = 0
		self.fee_pool = 0
		self.history = []
		self.fee_fraction = fee_fraction
		self.fee_to_liquidity_fraction = fee_to_liquidity_fraction # how much from the fee is reinvested to liqudity provision

	def create_event(self, liquidity) -> None:
		#self.initial_liquidity = liquidity
		self.add_liquidity(liquidity)

	def add_liquidity(self, amount):
		print("adding liquidity:", amount)
		self.initial_liquidity += amount

		self.lp_token += amount
		self.lp_yes += amount
		self.lp_no += amount

		# TODO: not sure those formulas are correct....
		total_pool = self.lp_yes + self.lp_no
		buy_price_yes_old = self.buy_price_yes
		self.buy_price_yes = (self.buy_price_yes + amount) /  total_pool
		self.sell_price_yes = (self.sell_price_yes + amount) /  total_pool
		self.buy_price_no = (self.buy_price_no + amount) /  total_pool
		self.sell_price_no = (self.sell_price_no + amount) / total_pool

		entry = ["add", "liquidity", amount, self.initial_liquidity, buy_price_yes_old,  self.buy_price_yes, 0, 0, self.lp_yes, self.lp_no, self.lp_token, self.fee_pool, 0 ,0]
		self._add_history(entry)

		# should return amount of outcome token
		# return (type, amount)

	# def remove_liquidity(amount):

	def buy_token(self, type, original_amount) -> Tuple[int, float]: #yes=1 | no = 0
		# keep invariant
		k = (self.lp_yes * self.lp_no)
		# take fee before any operation and store in fee_pool
		fee = original_amount * self.fee_fraction
		amount = original_amount - fee
		self.fee_pool += fee
		# add liquidity
		self.lp_token += amount

		if type:
			x = k / (self.lp_no + amount) - self.lp_yes
			tokens_return = amount - x

			buy_price_yes_old = self.buy_price_yes
			self.buy_price_yes = amount / tokens_return
			# calc slippage
			marginal_price_yes = self.lp_no / (self.lp_no + self.lp_yes)
			slippage_yes = (self.buy_price_yes - marginal_price_yes) / marginal_price_yes
			assert(slippage_yes > 0)

			# remove returned token form the pool, keep all no tokens
			self.lp_yes += x
			self.lp_no += amount

			entry = ["buy", "yes", original_amount, fee, buy_price_yes_old,  self.buy_price_yes, slippage_yes, tokens_return, self.lp_yes, self.lp_no, self.lp_token, self.fee_pool, 0, 0]
		else:
			x = k / (self.lp_yes + amount) - self.lp_no
			tokens_return = amount - x

			buy_price_no_old = self.buy_price_no
			self.buy_price_no = amount / tokens_return
			# calc slippage
			marginal_price_no = self.lp_yes / (self.lp_no + self.lp_yes)
			slippage_no = (self.buy_price_no - marginal_price_no) / marginal_price_no
			assert(slippage_no > 0)

			# remove returned token form the pool, keep all yes tokens
			self.lp_no += x
			self.lp_yes += amount

			entry = ["buy", "no", original_amount, fee, buy_price_no_old,  self.buy_price_no, slippage_no, tokens_return, self.lp_yes, self.lp_no, self.lp_token, self.fee_pool, 0, 0]



		# assert invariant, we use float and disregard rounding so must be within e ~ 0
		# print(f"invariant {k} {self.lp_yes * self.lp_no}")
		assert(abs(k - (self.lp_yes * self.lp_no)) < 0.000001)

		# calculate impermanent loss for initial LP assuming 50:50 split
		# convert matching yes/no into collateral
		withdraw_token = min(self.lp_yes, self.lp_no)
		impermanent_loss = self.initial_liquidity - withdraw_token
		#assert(impermanent_loss >= 0)
		# outstanding yes/no token may be converted at event outcome to reward or immediately traded
		if self.lp_yes > self.lp_no:
			outstanding_token = self.lp_yes - withdraw_token
		else:
			outstanding_token = self.lp_no - withdraw_token

		# impermanent loss at last position in history entry
		entry[-2] = impermanent_loss
		entry[-1] = outstanding_token
		self._add_history(entry)

		return (type, tokens_return)

	# def sell_token(type, amount):

	# def get_buy_price_yes():

	# def get_sell_price_yes():

	@property
	def history_as_dataframe(self) -> pd.DataFrame:
		return pd.DataFrame(data=self.history, columns=["activity", "type", "amount", "fee", "token_buy_price_old", "token_buy_price_new", "slippage", "returned tokens", "lp_yes", "lp_no", "lp_token", "fee_pool", "impermanent_loss", "loss_outstanding_tokens"])

	def save_history(self, name) -> None:
		df = self.history_as_dataframe
		with open(name, "wt") as f:
			df.to_csv(f, index=False, quoting=csv.QUOTE_NONNUMERIC)


	def _add_history(self, entry) -> None:
		# check entry size
		assert(len(entry) == 14)
		self.history.append(entry)


def run_experiment(name, cpmm: CPMM, n, prior_dist, betting_dist):
	# TODO: must have realistic model for betting behavior, for example
	# total bets volume cannot cross % of liquidity
	# individual bet cannot have slippage > 1% etc.
	bet_outcomes = prior_dist(n)
	bet_amounts = betting_dist(n)

	print(f"{name}: bet outcomes N/Y {np.bincount(bet_outcomes)}")

	for b, amount in zip(bet_outcomes, bet_amounts):
		cpmm.buy_token(b, amount)

		# adding fee_to_liquidity fraction to liquidity fee pool
		# note: liquidity is provided after buy such that added liquidity is available for next transaction
		if (cpmm.fee_to_liquidity_fraction != 0):
			reinvest_fee = (amount * cpmm.fee_fraction) * cpmm.fee_to_liquidity_fraction
			cpmm.add_liquidity(reinvest_fee)

	# print(cpmm.history)
	cpmm.save_history(f"{name}.csv")


def main():
	rng = default_rng()

	#experiment 1
	#1000 rounds, initial liquidity 50:50 1000 EVNT, betters prior 50:50, bets integer uniform range [1, 100]

	# cpmm = CPMM()
	# cpmm.create_event(1000)
	# run_experiment(
	# 	"experiment1",
	# 	cpmm,
	# 	1000,
	# 	lambda size: rng.binomial(1, 0.5, size),
	# 	lambda size: rng.integers(1, 100, endpoint=True, size=size)
	# )
	#
	# # experiment 2
	# # 1000 rounds, initial liquidity 50:50 1000 EVNT, betters prior 70:30, bets integer uniform range [1, 100]
	#
	# cpmm = CPMM()
	# cpmm.create_event(1000)
	# run_experiment(
	# 	"experiment2",
	# 	cpmm,
	# 	1000,
	# 	lambda size: rng.binomial(1, 0.7, size),
	# 	lambda size: rng.integers(1, 100, endpoint=True, size=size)
	# )
	#
	# # experiment 3
	# # 1000 rounds, initial liquidity 50:50 1000 EVNT, betters prior 70:30, bets integer uniform range [1, 100]
	# # fee 2% taken and not added to liquidity pool
	#
	# cpmm = CPMM(fee_fraction=0.02)
	# cpmm.create_event(1000)
	# run_experiment(
	# 	"experiment3",
	# 	cpmm,
	# 	1000,
	# 	lambda size: rng.binomial(1, 0.7, size),
	# 	lambda size: rng.integers(1, 100, endpoint=True, size=size)
	# )
	#
	# 	# experiment 4
	# # 1000 rounds, initial liquidity 50:50 1000 EVNT, betters prior 50:50, bets integer uniform range [1, 100]
	# # fee 2% taken and  50% added to liquidity pool

	cpmm = CPMM(fee_fraction=0.02, fee_to_liquidity_fraction=0.5)
	cpmm.create_event(1000)
	run_experiment(
		"experiment4",
		cpmm,
		1000,
		lambda size: rng.binomial(1, 0.5, size),
		lambda size: rng.integers(1, 100, endpoint=True, size=size)
	)

if __name__ == "__main__":
    main()
