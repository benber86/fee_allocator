from typing import Callable

import boa
import pytest
from moccasin.boa_tools import VyperContract
from moccasin.config import get_config
from moccasin.moccasin_account import MoccasinAccount
from src import GlobalFeeSplitter
import moccasin

EMPTY_COMPENSATION = (0, (0, 0, 0), 0, 0, False)

FEE_COLLECTOR_ADMIN = "0x40907540d8a6C65c637785e8f8B742ae6b0b9968"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ETH_ADDRESS = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
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
def global_fee_splitter(actual_fee_distributor, actual_fee_collector, admin) -> VyperContract:
    return GlobalFeeSplitter.deploy(
        actual_fee_distributor, actual_fee_collector, admin
    )



@pytest.fixture(scope="session", autouse=True)
def set_epoch_to_forward(actual_fee_collector):  # move forward, so all time travels lead to positive values

    boa.env.time_travel(seconds=52 * WEEK)
    timeframe = actual_fee_collector.epoch_time_frame(8) # FORWARD period = 8
    seconds = timeframe[0] - boa.env.evm.vm.state.timestamp
    extra_week = WEEK * (seconds // WEEK)
    boa.env.time_travel(seconds=seconds + extra_week)


@pytest.fixture(scope="session", autouse=True)
def add_fee_splitter_to_hooker(actual_hooker, actual_crvusd, global_fee_splitter):
    with boa.env.prank(FEE_COLLECTOR_ADMIN):
        actual_hooker.set_hooks(
            [(global_fee_splitter.address,
              global_fee_splitter.distribute_fees.prepare_calldata(actual_crvusd.address),
              EMPTY_COMPENSATION, True
              )]
        )
        actual_hooker.one_time_hooks([(
            actual_crvusd.address,
            actual_crvusd.approve.prepare_calldata(global_fee_splitter.address, 2 ** 256 - 1),EMPTY_COMPENSATION,False

        )], [(0, 0, b"")])

