import time
from typing import Callable

import boa
import pytest
from moccasin.boa_tools import VyperContract
from moccasin.config import get_config
from moccasin.moccasin_account import MoccasinAccount
from src import FeeAllocator
import moccasin

EMPTY_COMPENSATION = (0, (0, 0, 0), 0, 0, False)

FEE_COLLECTOR_ADMIN = "0x40907540d8a6C65c637785e8f8B742ae6b0b9968"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
WEEK = 7 * 24 * 3600


@pytest.fixture(scope="session")
def actual_fee_collector() -> VyperContract:
    return get_config().get_active_network().manifest_named("fee_collector")


@pytest.fixture(scope="session")
def actual_hooker() -> VyperContract:
    return get_config().get_active_network().manifest_named("hooker")


@pytest.fixture(scope="session")
def actual_crvusd() -> VyperContract:
    return get_config().get_active_network().manifest_named("crvusd")


@pytest.fixture(scope="session")
def actual_fee_distributor() -> VyperContract:
    return get_config().get_active_network().manifest_named("fee_distributor")


@pytest.fixture(scope="session")
def crv_token() -> VyperContract:
    return get_config().get_active_network().manifest_named("crv_token")


@pytest.fixture(scope="session")
def vecrv() -> VyperContract:
    return get_config().get_active_network().manifest_named("vecrv")


@pytest.fixture(scope="session")
def community_fund() -> VyperContract:
    return get_config().get_active_network().manifest_named("community_fund")


@pytest.fixture(scope="session")
def voting() -> VyperContract:
    return get_config().get_active_network().manifest_named("voting")


@pytest.fixture(scope="session")
def agent() -> VyperContract:
    return get_config().get_active_network().manifest_named("agent")


@pytest.fixture(scope="session")
def admin() -> MoccasinAccount:
    return moccasin.config.get_active_network().get_default_account()


@pytest.fixture(scope="session")
def fee_receiver():
    return boa.env.generate_address()


@pytest.fixture(scope="session")
def multiple_fee_receivers():
    return [boa.env.generate_address() for _ in range(10)]


@pytest.fixture(scope="session")
def crvusd_minter(actual_crvusd):
    return actual_crvusd.minter()


@pytest.fixture(scope="session")
def mint_to_receiver(actual_crvusd, crvusd_minter) -> Callable[[str, int], None]:
    def inner(receiver: str, amount: int):
        with boa.env.prank(crvusd_minter):
            actual_crvusd.mint(receiver, amount)
    return inner


@pytest.fixture(scope="session")
def fee_allocator(
    actual_fee_distributor, actual_fee_collector, admin
) -> VyperContract:
    return FeeAllocator.deploy(actual_fee_distributor, actual_fee_collector, admin)


@pytest.fixture(scope="session", autouse=True)
def lock_vecrv_on_main(crv_token, vecrv, admin):
    amount = int(10_000 * 1e18)
    with boa.env.prank(vecrv.address):
        crv_token.transfer(admin, amount)
    with boa.env.prank(admin.address):
        crv_token.approve(vecrv, amount)
        vecrv.create_lock(amount, int(time.time()) + WEEK * 52 * 4)

@pytest.fixture(scope="session", autouse=True)
def set_epoch_to_forward(
    actual_fee_collector,
):  # move forward, so all time travels lead to positive values

    boa.env.time_travel(seconds=52 * WEEK)
    timeframe = actual_fee_collector.epoch_time_frame(8)  # FORWARD period = 8
    seconds = timeframe[0] - boa.env.evm.vm.state.timestamp
    extra_week = WEEK * (seconds // WEEK)
    boa.env.time_travel(seconds=seconds + extra_week)


@pytest.fixture(scope="session", autouse=True)
def add_fee_allocator_to_hooker(actual_hooker, actual_crvusd, fee_allocator):
    with boa.env.prank(FEE_COLLECTOR_ADMIN):
        actual_hooker.set_hooks(
            [
                (
                    fee_allocator.address,
                    fee_allocator.distribute_fees.prepare_calldata(),
                    EMPTY_COMPENSATION,
                    True,
                )
            ]
        )
        actual_hooker.one_time_hooks(
            [
                (
                    actual_crvusd.address,
                    actual_crvusd.approve.prepare_calldata(
                        fee_allocator.address, 2**256 - 1
                    ),
                    EMPTY_COMPENSATION,
                    False,
                )
            ],
            [(0, 0, b"")],
        )
