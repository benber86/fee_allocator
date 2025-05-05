import boa

from tests.conftest import FEE_COLLECTOR_ADMIN


def test_distribute(actual_fee_collector,
                    actual_fee_distributor,
                    global_fee_splitter,
                    actual_crvusd,
                    default_account,
                    ):


    with boa.env.prank(FEE_COLLECTOR_ADMIN):
        actual_fee_collector.forward([(0,0,b'')], default_account.address)
