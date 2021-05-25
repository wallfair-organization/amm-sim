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
		# assert(fee_fraction >= fee_to_liquidity_fraction)

		# amount of initial liquidity provided
		self.initial_liquidity = 0
		# total amount of liquidity
		self.liquidity = 0
		# total amount of collateral token
		self.lp_token = 0
		# yes tokens in the pool
		self.lp_yes = 0
		# no tokens in the pool
		self.lp_no = 0
		# outstanding tokens held by LP
		self.outstanding_yes = 0
		self.outstanding_no = 0

		self.fee_pool = 0
		self.history = []
		self.fee_fraction = fee_fraction
		self.fee_to_liquidity_fraction = fee_to_liquidity_fraction # how much from the fee is reinvested to liqudity provision

	def create_event(self, intial_liquidity, initial_yes_to_no = 1) -> Tuple[int, float]:
		assert(initial_yes_to_no > 0)
		self.initial_liquidity = intial_liquidity
		rv = self._add_liquidity(intial_liquidity, initial_yes_to_no)
		n_p = self.lp_yes / self.lp_no
		# print(f"invariant P {initial_yes_to_no} {n_p}")
		assert(abs(initial_yes_to_no - n_p) < 0.000001)
		return rv

	def add_liquidity(self, amount) -> Tuple[int, float]:
		assert(self.lp_token > 0)
		# yes to no must be invariant when liquidity is added
		p = self.lp_yes / self.lp_no
		rv = self._add_liquidity(amount, p)
		n_p = self.lp_yes / self.lp_no
		# assert invariant, we use float and disregard rounding so must be within e ~ 0
		# print(f"invariant P {p} {n_p}")
		assert(abs(p - n_p) < 0.000001)

		return rv

	def _add_liquidity(self, amount, yes_to_no) -> Tuple[int, float]:
		# print("adding liquidity:", amount)
		self.liquidity += amount
		self.lp_token += amount

		# get token type from the ratio
		type = 1 if yes_to_no >= 1 else 0 

		if type:
			# more into YES bucket, NO is returned
			old_lp_no = self.lp_no
			self.lp_no = (amount + self.lp_yes) / yes_to_no
			self.lp_yes += amount

			tokens_return = amount + old_lp_no - self.lp_no
			self.outstanding_no += tokens_return
		else:
			# more into NO bucket, YES is returned
			old_lp_yes = self.lp_yes
			self.lp_yes = (amount + self.lp_no) * yes_to_no
			self.lp_no += amount

			tokens_return = amount + old_lp_yes - self.lp_yes
			self.outstanding_yes += tokens_return

		entry = ["add", "liquidity", amount, 0, yes_to_no, 0, tokens_return, self.lp_yes, self.lp_no, self.lp_token, self.liquidity, self.fee_pool, 0 ,0]
		self._add_history(entry)

		# should return amount of outcome token
		return (type, amount)

	# def remove_liquidity(amount):

	def buy_token(self, type, original_amount) -> Tuple[int, float]: #yes=1 | no = 0
		# take fee before any operation and store in fee_pool
		fee = original_amount * self.fee_fraction
		amount = original_amount - fee
		self.fee_pool += fee
		# adding fee_to_liquidity fraction to liquidity fee pool
		# note: liquidity is provided before buy such that added liquidity is available for current transaction
		if (self.fee_to_liquidity_fraction > 0):
			reinvest_fee = fee * self.fee_to_liquidity_fraction
			self.add_liquidity(reinvest_fee)

		# keep invariant
		k = (self.lp_yes * self.lp_no)

		# add liquidity
		self.lp_token += amount

		if type:
			tokens_return, x = self.calc_buy(type, amount)
			buy_price_yes = amount / tokens_return
			# calc slippage
			slippage_yes = self.calc_slippage(type, amount)
			assert (slippage_yes > 0), f"slippage_yes {slippage_yes} <= 0"

			# remove returned token form the pool, keep all no tokens
			self.lp_yes += x
			self.lp_no += amount

			entry = ["buy", "yes", original_amount, fee, buy_price_yes, slippage_yes, tokens_return, self.lp_yes, self.lp_no, self.lp_token, self.liquidity, self.fee_pool, 0, 0]
		else:
			tokens_return, x = self.calc_buy(type, amount)
			buy_price_no = amount / tokens_return
			slippage_no = self.calc_slippage(type, amount)
			assert (slippage_no > 0),  f"slippage_no {slippage_no} <= 0"

			# remove returned token form the pool, keep all yes tokens
			self.lp_no += x
			self.lp_yes += amount

			entry = ["buy", "no", original_amount, fee, buy_price_no, slippage_no, tokens_return, self.lp_yes, self.lp_no, self.lp_token, self.liquidity, self.fee_pool, 0, 0]



		# assert invariant, we use float and disregard rounding so must be within e ~ 0
		inv_div = abs(k - (self.lp_yes * self.lp_no))
		# use variable epsilon - float numbers suck due to scaling
		inv_eps = min(self.lp_no, self.lp_yes) / 100000000
		if inv_div > inv_eps :
			print(f"invariant K {k} {self.lp_yes * self.lp_no} == {inv_div}, lp_yes {self.lp_yes} lp_no {self.lp_no} eps {inv_eps}")
		assert(inv_div < inv_eps)

		impermanent_loss = self.calc_impermanent_loss()
		assert(impermanent_loss >= 0)
		# outstanding yes/no token may be converted at event outcome to reward or immediately traded
		outstanding_token = self.calc_outstanding_token()

		# impermanent loss at last position in history entry
		entry[-2] = impermanent_loss
		entry[-1] = outstanding_token[1]
		self._add_history(entry)

		return (type, tokens_return)

	def calc_withdrawable_liquidity(self) -> float:
		# collateral taken from the pool and tokens returned when adding liquidity
		return min(self.lp_yes + self.outstanding_yes, self.lp_no + self.outstanding_no)

	def calc_payout(self) -> float:
		# how big is reward after all liquidity is removed
		return self.lp_token - self.calc_withdrawable_liquidity()

	def calc_outstanding_token(self) -> Tuple[int, float]:
		# outcome tokens going to LP on top of removed liquidity
		withdraw_token = self.calc_withdrawable_liquidity()
		total_yes = self.lp_yes + self.outstanding_yes
		total_no = self.lp_no + self.outstanding_no
		if total_yes > total_no:
			outstanding_token = (1, total_yes - withdraw_token)
		else:
			outstanding_token = (0, total_no - withdraw_token)
		return outstanding_token

	def calc_impermanent_loss(self) -> float:
		withdraw_token = self.calc_withdrawable_liquidity()
		return self.liquidity - withdraw_token

	def calc_buy(self, type, amount) -> Tuple[float, float]:
		k = (self.lp_yes * self.lp_no)
		if type:
			x = k / (self.lp_no + amount) - self.lp_yes
		else:
			x = k / (self.lp_yes + amount) - self.lp_no

		# (tokens returned to the user, amm pool delta)
		return amount - x, x

	def calc_marginal_price(self, type) -> float:
		pool_total = (self.lp_no + self.lp_yes)
		return (self.lp_no if type else self.lp_yes) / pool_total

	def calc_slippage(self, type, amount) -> float:
		tokens_return, _ = self.calc_buy(type, amount)
		buy_price = amount / tokens_return
		marginal_price = self.calc_marginal_price(type)
		return (buy_price - marginal_price) / buy_price

	@staticmethod
	def calc_british_odds(returned_tokens, amount) -> float:
		# british odds https://www.investopedia.com/articles/investing/042115/betting-basics-fractional-decimal-american-moneyline-odds.asp
		# shows the reward on top of stake as a decimal fraction to the stake
		# (TODO: we could use Fraction class of python for nice odds representation)
		# may be negative when due to cpmm inefficiencies
		return (returned_tokens - amount) / amount

	# def sell_token(type, amount):

	# def get_buy_price_yes():

	# def get_sell_price_yes():

	_csv_headers = [
		"activity", "type", "amount", "fee", "token_buy_sell_price",
		"slippage", "returned tokens", "lp_yes", "lp_no", "lp_token",
		"liquidity", "fee_pool", "impermanent_loss", "loss_outstanding_tokens"
	]

	@property
	def history_as_dataframe(self) -> pd.DataFrame:
		return pd.DataFrame(data=self.history, columns=CPMM._csv_headers)

	def save_history(self, name) -> None:
		df = self.history_as_dataframe
		with open(name, "wt") as f:
			df.to_csv(f, index=False, quoting=csv.QUOTE_NONNUMERIC)


	def _add_history(self, entry) -> None:
		# check entry size
		assert(len(entry) == len(CPMM._csv_headers))
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

	# print(cpmm.history)
	cpmm.save_history(f"{name}.csv")


def main():
	rng = default_rng()

	# experiment 1
	# 1000 rounds, initial liquidity 50:50 1000 EVNT, betters prior 50:50, bets integer uniform range [1, 100]

	cpmm = CPMM()
	cpmm.create_event(1000)
	run_experiment(
		"experiment1",
		cpmm,
		1000,
		lambda size: rng.binomial(1, 0.5, size),
		lambda size: rng.integers(1, 100, endpoint=True, size=size)
	)
	
	# experiment 2
	# 1000 rounds, initial liquidity 50:50 1000 EVNT, betters prior 70:30, bets integer uniform range [1, 100]
	
	cpmm = CPMM()
	cpmm.create_event(1000)
	run_experiment(
		"experiment2",
		cpmm,
		1000,
		lambda size: rng.binomial(1, 0.7, size),
		lambda size: rng.integers(1, 100, endpoint=True, size=size)
	)
	
	# experiment 3
	# 1000 rounds, initial liquidity 50:50 1000 EVNT, betters prior 70:30, bets integer uniform range [1, 100]
	# fee 2% taken and not added to liquidity pool
	
	cpmm = CPMM(fee_fraction=0.02)
	cpmm.create_event(1000)
	run_experiment(
		"experiment3",
		cpmm,
		1000,
		lambda size: rng.binomial(1, 0.7, size),
		lambda size: rng.integers(1, 100, endpoint=True, size=size)
	)
	
	# experiment 4
	# 1000 rounds, initial liquidity 50:50 1000 EVNT, betters prior 50:50, bets integer uniform range [1, 100]
	# fee 2% taken and  50% added to liquidity pool

	cpmm = CPMM(fee_fraction=0.02, fee_to_liquidity_fraction=0.5)
	cpmm.create_event(1000)
	run_experiment(
		"experiment4",
		cpmm,
		1000,
		lambda size: rng.binomial(1, 0.5, size),
		lambda size: rng.integers(1, 100, endpoint=True, size=size)
	)

	# experiment 5
	# 1000 rounds, initial liquidity 1:3 1000 EVNT, betters prior 50:50, bets integer uniform range [1, 100]
	# fee 2% taken and  50% added to liquidity pool

	cpmm = CPMM(fee_fraction=0.02, fee_to_liquidity_fraction=0.5)
	cpmm.create_event(1000)
	run_experiment(
		"experiment5",
		cpmm,
		1000,
		lambda size: rng.binomial(1, 0.5, size),
		lambda size: rng.integers(1, 100, endpoint=True, size=size)
	)

if __name__ == "__main__":
    main()
