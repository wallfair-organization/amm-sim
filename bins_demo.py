from cpmm import CPMM

cpmm = CPMM(0.01)
cpmm.create_event(1000, initial_yes_to_no=0.7)


calc_sell = lambda t, a: -cpmm.calc_buy(t, -a)[0]

eps = 0.001

# this is price of 1 EVNT in outcome tokens
marginal_r = calc_sell(0, eps) / eps
print(f"marginal_r{marginal_r}")

# this is price of 1 outcome token in events
marginal_p = 1/marginal_r
print(f"marginal_p {marginal_p}")

# marginal_p is higher than real p due to slippage
slippage_p = 1 / calc_sell(0, 1)
print(f"slippage_price check {slippage_p} < {marginal_p}")
# so it's useful to establish maximum range

sell_amount = 100  # outcome tokens

# check if binary search will exit. you cannot sell less than our eps
assert eps < calc_sell(0, marginal_p * sell_amount)

# we want to sell 100 outcome tokens, this is approx number of EVNT
maximum_range = marginal_p * sell_amount
# print(maximum_range) 
minimum_range = 0

# approximation precision in outstanding tokens
approx_eps = 0.001

# binary search
i = 1
while minimum_range <= maximum_range:
    mid_range = (minimum_range + maximum_range) / 2
    approx_sell = calc_sell(0, mid_range)
    # exit condition. we want to sell a little bit less than sell_amount in case when sell_amount is max
    if approx_sell < sell_amount and sell_amount - approx_sell <= approx_eps:
        break;
    if approx_sell < sell_amount:
        minimum_range = mid_range
    else:
        maximum_range = mid_range
    i += 1

# our quote in EVNT for 100 outcome tokens
print(mid_range)
print(f"{i} iterations")

# verify
verify_sell = calc_sell(0, mid_range)
print(f"quote {mid_range}, will receive {verify_sell} where exact wanted {sell_amount}, staying within {sell_amount - verify_sell} < {approx_eps}")