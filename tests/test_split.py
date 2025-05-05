import boa

from tests.conftest import FEE_COLLECTOR_ADMIN

AMOUNT_TO_DISTRIBUTE = int(100_000 * 1e18)

def test_distribute(actual_fee_collector,
                    actual_fee_distributor,
                    global_fee_splitter,
                    actual_crvusd,
                    default_account,
                    fee_receiver,
                    mint_to_receiver,
                    ):

    with boa.env.prank(FEE_COLLECTOR_ADMIN):
        # ensure enough crvUSD for distribution
        mint_to_receiver(actual_fee_collector.address, AMOUNT_TO_DISTRIBUTE)

        pre_distribution_collector_balance = actual_crvusd.balanceOf(actual_fee_collector.address)
        pre_distribution_caller_balance = actual_crvusd.balanceOf(default_account)
        pre_distribution_receiver_balance = actual_crvusd.balanceOf(fee_receiver)
        pre_distribution_distributor_balance = actual_crvusd.balanceOf(actual_fee_distributor)

        actual_fee_collector.forward([(0,0,b'')], default_account.address)

        post_distribution_collector_balance = actual_crvusd.balanceOf(actual_fee_collector.address)
        post_distribution_caller_balance = actual_crvusd.balanceOf(default_account)
        post_distribution_receiver_balance = actual_crvusd.balanceOf(fee_receiver)
        post_distribution_distributor_balance = actual_crvusd.balanceOf(actual_fee_distributor)

        collector_pre = pre_distribution_collector_balance * 1e-18
        collector_post = post_distribution_collector_balance * 1e-18
        collector_diff = collector_post - collector_pre

        caller_pre = pre_distribution_caller_balance * 1e-18
        caller_post = post_distribution_caller_balance * 1e-18
        caller_diff = caller_post - caller_pre

        receiver_pre = pre_distribution_receiver_balance * 1e-18
        receiver_post = post_distribution_receiver_balance * 1e-18
        receiver_diff = receiver_post - receiver_pre

        distributor_pre = pre_distribution_distributor_balance * 1e-18
        distributor_post = post_distribution_distributor_balance * 1e-18
        distributor_diff = distributor_post - distributor_pre

        print("Entity      | Pre-distribution | Post-distribution | Difference")
        print("-----------|-----------------|------------------|------------")
        print(f"Collector   | {collector_pre:.2f} | {collector_post:.2f} | {collector_diff:.2f}")
        print(f"Caller      | {caller_pre:.2f} | {caller_post:.2f} | {caller_diff:.2f}")
        print(f"Receiver    | {receiver_pre:.2f} | {receiver_post:.2f} | {receiver_diff:.2f}")
        print(f"Distributor    | {distributor_pre:.2f} | {distributor_post:.2f} | {distributor_diff:.2f}")