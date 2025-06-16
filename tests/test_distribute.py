import boa
import pytest

from tests.conftest import FEE_COLLECTOR_ADMIN

AMOUNT_TO_DISTRIBUTE = int(100_000 * 1e18)


def test_distribute_no_receivers(
    actual_fee_collector,
    actual_fee_distributor,
    fee_allocator,
    actual_crvusd,
    admin,
    fee_receiver,
    mint_to_receiver,
):

    collector_fee = actual_fee_collector.fee(8)
    with boa.env.prank(FEE_COLLECTOR_ADMIN):
        # ensure enough crvUSD for distribution
        mint_to_receiver(actual_fee_collector.address, AMOUNT_TO_DISTRIBUTE)

    pre_distribution_collector_balance = actual_crvusd.balanceOf(
        actual_fee_collector.address
    )
    pre_distribution_caller_balance = actual_crvusd.balanceOf(admin)
    pre_distribution_distributor_balance = actual_crvusd.balanceOf(
        actual_fee_distributor
    )

    actual_fee_collector.forward([(0, 0, b"")], admin.address)

    post_distribution_collector_balance = actual_crvusd.balanceOf(
        actual_fee_collector.address
    )
    post_distribution_caller_balance = actual_crvusd.balanceOf(admin)
    post_distribution_distributor_balance = actual_crvusd.balanceOf(
        actual_fee_distributor
    )

    effective_caller_fee = (
        pre_distribution_collector_balance * collector_fee * 1e-18
    )
    assert post_distribution_caller_balance == pytest.approx(
        pre_distribution_caller_balance + effective_caller_fee
    )
    assert post_distribution_collector_balance == 0
    assert post_distribution_distributor_balance == pytest.approx(
        pre_distribution_collector_balance
        + pre_distribution_distributor_balance
        - effective_caller_fee
    )


def test_distribute_single_receiver(
    actual_fee_collector,
    actual_fee_distributor,
    fee_allocator,
    actual_crvusd,
    admin,
    fee_receiver,
    mint_to_receiver,
):
    # Set up a single receiver with 2000 bps (20%)
    receiver_weight = 2000
    with boa.env.prank(admin.address):
        fee_allocator.set_receiver(fee_receiver, receiver_weight)

    collector_fee = actual_fee_collector.fee(8)
    with boa.env.prank(FEE_COLLECTOR_ADMIN):
        mint_to_receiver(actual_fee_collector.address, AMOUNT_TO_DISTRIBUTE)

    pre_distribution_collector_balance = actual_crvusd.balanceOf(
        actual_fee_collector.address
    )
    pre_distribution_caller_balance = actual_crvusd.balanceOf(admin)
    pre_distribution_distributor_balance = actual_crvusd.balanceOf(
        actual_fee_distributor
    )
    pre_distribution_receiver_balance = actual_crvusd.balanceOf(fee_receiver)

    actual_fee_collector.forward([(0, 0, b"")], admin.address)

    post_distribution_collector_balance = actual_crvusd.balanceOf(
        actual_fee_collector.address
    )
    post_distribution_caller_balance = actual_crvusd.balanceOf(admin)
    post_distribution_distributor_balance = actual_crvusd.balanceOf(
        actual_fee_distributor
    )
    post_distribution_receiver_balance = actual_crvusd.balanceOf(fee_receiver)

    effective_caller_fee = (
        pre_distribution_collector_balance * collector_fee * 1e-18
    )
    remaining_amount = (
        pre_distribution_collector_balance - effective_caller_fee
    )
    receiver_amount = remaining_amount * receiver_weight // 10000
    distributor_amount = remaining_amount - receiver_amount

    assert post_distribution_caller_balance == pytest.approx(
        pre_distribution_caller_balance + effective_caller_fee
    )
    assert post_distribution_collector_balance == 0
    assert post_distribution_receiver_balance == pytest.approx(
        pre_distribution_receiver_balance + receiver_amount
    )
    assert post_distribution_distributor_balance == pytest.approx(
        pre_distribution_distributor_balance + distributor_amount
    )


def test_distribute_multiple_receivers(
    actual_fee_collector,
    actual_fee_distributor,
    fee_allocator,
    actual_crvusd,
    admin,
    multiple_fee_receivers,
    mint_to_receiver,
):
    # Reset any existing receivers
    with boa.env.prank(admin.address):
        for receiver in range(fee_allocator.n_receivers()):
            fee_allocator.remove_receiver(receiver)

    receiver_weights = [500, 1000, 1500, 2000]  # Total: 5000 bps (50%)
    receivers_to_use = multiple_fee_receivers[: len(receiver_weights)]

    configs = []
    for i, weight in enumerate(receiver_weights):
        configs.append((receivers_to_use[i], weight))

    with boa.env.prank(admin.address):
        fee_allocator.set_multiple_receivers(configs)

    collector_fee = actual_fee_collector.fee(8)
    with boa.env.prank(FEE_COLLECTOR_ADMIN):
        mint_to_receiver(actual_fee_collector.address, AMOUNT_TO_DISTRIBUTE)

    pre_distribution_collector_balance = actual_crvusd.balanceOf(
        actual_fee_collector.address
    )
    pre_distribution_caller_balance = actual_crvusd.balanceOf(admin)
    pre_distribution_distributor_balance = actual_crvusd.balanceOf(
        actual_fee_distributor
    )
    pre_distribution_receiver_balances = [
        actual_crvusd.balanceOf(receiver) for receiver in receivers_to_use
    ]

    actual_fee_collector.forward([(0, 0, b"")], admin.address)

    post_distribution_collector_balance = actual_crvusd.balanceOf(
        actual_fee_collector.address
    )
    post_distribution_caller_balance = actual_crvusd.balanceOf(admin)
    post_distribution_distributor_balance = actual_crvusd.balanceOf(
        actual_fee_distributor
    )
    post_distribution_receiver_balances = [
        actual_crvusd.balanceOf(receiver) for receiver in receivers_to_use
    ]

    effective_caller_fee = (
        pre_distribution_collector_balance * collector_fee * 1e-18
    )
    remaining_amount = (
        pre_distribution_collector_balance - effective_caller_fee
    )

    total_to_receivers = 0
    for i, weight in enumerate(receiver_weights):
        receiver_amount = remaining_amount * weight // 10000
        total_to_receivers += receiver_amount
        assert post_distribution_receiver_balances[i] == pytest.approx(
            pre_distribution_receiver_balances[i] + receiver_amount
        )

    distributor_amount = remaining_amount - total_to_receivers

    assert post_distribution_caller_balance == pytest.approx(
        pre_distribution_caller_balance + effective_caller_fee
    )
    assert post_distribution_collector_balance == 0
    assert post_distribution_distributor_balance == pytest.approx(
        pre_distribution_distributor_balance + distributor_amount
    )


def test_distribute_fees_no_balance(
    fee_allocator, actual_hooker, actual_crvusd
):
    with boa.env.prank(actual_hooker.address):
        with pytest.raises(Exception):
            fee_allocator.distribute_fees()
