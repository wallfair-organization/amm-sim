from cpmm import CPMM

def run_market(initial_liquidity, fee_fraction, max_turnover_fraction, max_yes_odds, max_slippage, fee_to_liquidity_fraction) -> CPMM:
    cpmm = CPMM(fee_fraction=fee_fraction, fee_to_liquidity_fraction=fee_to_liquidity_fraction)
    amount = initial_liquidity * max_slippage
    no_amount = amount * max_yes_odds
    cpmm.create_event(initial_liquidity)
    # how many steps, each steps puts amount for YES and amount * odds into no
    turnover_steps = (max_turnover_fraction * initial_liquidity) // (amount + no_amount) + 1
    # vals = []
    for i in range(1, int(turnover_steps)):
        cpmm.buy_token(1, amount)
        cpmm.buy_token(0, no_amount)
    return cpmm


# this runs simulation for three "break even" scenarions: with loss, break even and profit
# all market have the same volume, liquidity and initial odds
# what is different is the betting behavior of users that impact impermanent loss

initial_liquidity = 1000000
# loss market
cpmm = run_market(initial_liquidity, 0.03, 16, 8, 0.02, 0)
cpmm.save_history(f"loss_market.csv")
print((cpmm.fee_pool - cpmm.calc_impermanent_loss())*100/initial_liquidity)

# break even market
cpmm = run_market(initial_liquidity, 0.03, 16, 3.39, 0.02, 0)
cpmm.save_history(f"even_market.csv")
print((cpmm.fee_pool - cpmm.calc_impermanent_loss())*100/initial_liquidity)

# profit even market
cpmm = run_market(initial_liquidity, 0.03, 16, 1.5, 0.02, 0)
cpmm.save_history(f"profit_market.csv")
print((cpmm.fee_pool - cpmm.calc_impermanent_loss())*100/initial_liquidity)