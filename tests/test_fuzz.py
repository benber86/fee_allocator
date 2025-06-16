import boa
import pytest
from boa.test.strategies import strategy
from hypothesis import settings
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
    run_state_machine_as_test,
)

from tests.conftest import ZERO_ADDRESS


@pytest.mark.fuzz
class FeeAllocatorStateMachine(RuleBasedStateMachine):
    def __init__(
        self,
        fee_allocator,
        admin,
        actual_crvusd,
        actual_hooker,
        actual_fee_distributor,
        mint_to_receiver,
    ):
        super().__init__()
        self.fee_allocator = fee_allocator
        self.admin = admin
        self.actual_crvusd = actual_crvusd
        self.actual_hooker = actual_hooker
        self.actual_fee_distributor = actual_fee_distributor
        self.mint_to_receiver = mint_to_receiver
        self.active_receivers = []
        self.receiver_weights = {}
        self.total_weight = 0

    @rule(
        receiver=strategy("address"),
        weight=strategy("uint256", min_value=1, max_value=5000),
    )
    def set_receiver(self, receiver, weight):
        if receiver == ZERO_ADDRESS:
            return
        if (
            self.fee_allocator.n_receivers()
            >= self.fee_allocator.MAX_RECEIVERS()
        ):
            return

        with boa.env.prank(self.admin.address):
            try:
                old_weight = self.fee_allocator.receiver_weights(receiver)
                new_total = self.total_weight - old_weight + weight

                if new_total <= 5000:
                    self.fee_allocator.set_receiver(receiver, weight)

                    if old_weight == 0:
                        self.active_receivers.append(receiver)

                    self.receiver_weights[receiver] = weight
                    self.total_weight = new_total
            except Exception as e:
                print("Unexpected exception in set_receiver")
                raise e

    @rule(index=strategy("uint256", min_value=0, max_value=9))
    def remove_receiver(self, index):
        if not self.active_receivers:
            return

        if index >= len(self.active_receivers):
            return

        receiver = self.active_receivers[index]

        with boa.env.prank(self.admin.address):
            try:
                weight = self.fee_allocator.receiver_weights(receiver)
                self.fee_allocator.remove_receiver(receiver)

                self.active_receivers.remove(receiver)
                self.total_weight -= weight
                self.receiver_weights[receiver] = 0
            except Exception as e:
                print("Unexpected exception in remove_receiver")
                raise e

    @rule(
        amount=strategy("uint256", min_value=1000, max_value=1000000 * 10**18)
    )
    def distribute_fees(self, amount):
        if amount == 0:
            return

        with boa.env.prank(self.actual_hooker.address):
            try:
                self.mint_to_receiver(self.actual_hooker.address, amount)

                pre_balances = {
                    receiver: self.actual_crvusd.balanceOf(receiver)
                    for receiver in self.active_receivers
                }
                pre_distributor_balance = self.actual_crvusd.balanceOf(
                    self.actual_fee_distributor.address
                )

                self.fee_allocator.distribute_fees(self.actual_crvusd.address)

                post_balances = {
                    receiver: self.actual_crvusd.balanceOf(receiver)
                    for receiver in self.active_receivers
                }
                post_distributor_balance = self.actual_crvusd.balanceOf(
                    self.actual_fee_distributor.address
                )

                total_distributed = 0
                for receiver in self.active_receivers:
                    received = post_balances[receiver] - pre_balances[receiver]
                    expected = (
                        amount * self.receiver_weights[receiver] // 10000
                    )
                    assert abs(received - expected) <= len(
                        self.active_receivers
                    )
                    total_distributed += received

                distributor_received = (
                    post_distributor_balance - pre_distributor_balance
                )
                assert (
                    abs(total_distributed + distributor_received - amount)
                    <= len(self.active_receivers) + 1
                )

            except Exception as e:
                print("Unexpected exception in distribute_fees")
                raise e

    @invariant()
    def total_weight_invariant(self):
        assert self.fee_allocator.total_weight() == self.total_weight
        assert self.fee_allocator.total_weight() <= 5000

    @invariant()
    def receiver_count_invariant(self):
        assert self.fee_allocator.n_receivers() == len(self.active_receivers)
        assert self.fee_allocator.n_receivers() <= 10

    @invariant()
    def distributor_weight_invariant(self):
        assert (
            self.fee_allocator.distributor_weight()
            == 10000 - self.total_weight
        )


@pytest.mark.fuzz
def test_fee_allocator(
    fee_allocator,
    admin,
    actual_crvusd,
    actual_hooker,
    actual_fee_distributor,
    mint_to_receiver,
):
    run_state_machine_as_test(
        lambda: FeeAllocatorStateMachine(
            fee_allocator,
            admin,
            actual_crvusd,
            actual_hooker,
            actual_fee_distributor,
            mint_to_receiver,
        ),
        settings=settings(max_examples=1000, stateful_step_count=50),
    )
