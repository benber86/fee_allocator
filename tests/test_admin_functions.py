import boa
import pytest

from tests.conftest import ZERO_ADDRESS


def test_set_receiver_zero_address(global_fee_splitter, admin):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            global_fee_splitter.set_receiver(ZERO_ADDRESS, 1000)


def test_set_receiver_zero_weight(global_fee_splitter, admin, fee_receiver):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            global_fee_splitter.set_receiver(fee_receiver, 0)


def test_set_receiver_exceeding_max_weight(global_fee_splitter, admin, fee_receiver):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            global_fee_splitter.set_receiver(fee_receiver, 5001)


def test_set_receiver_valid(global_fee_splitter, admin, fee_receiver):
    with boa.env.prank(admin.address):
        global_fee_splitter.set_receiver(fee_receiver, 1000)
        assert global_fee_splitter.receiver_weights(fee_receiver) == 1000
        assert global_fee_splitter.total_weight() == 1000


def test_update_receiver_weight(global_fee_splitter, admin, fee_receiver):
    with boa.env.prank(admin.address):
        global_fee_splitter.set_receiver(fee_receiver, 1000)
        global_fee_splitter.set_receiver(fee_receiver, 2000)
        assert global_fee_splitter.receiver_weights(fee_receiver) == 2000
        assert global_fee_splitter.total_weight() == 2000


def test_set_multiple_receivers_empty_array(global_fee_splitter, admin):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            global_fee_splitter.set_multiple_receivers([])


def test_set_multiple_receivers_valid(
    global_fee_splitter, admin, multiple_fee_receivers
):
    with boa.env.prank(admin.address):
        receivers = multiple_fee_receivers[:3]
        weights = [1000, 1500, 2000]
        configs = [(receivers[i], weights[i]) for i in range(3)]

        global_fee_splitter.set_multiple_receivers(configs)

        for i in range(3):
            assert global_fee_splitter.receiver_weights(receivers[i]) == weights[i]

        assert global_fee_splitter.total_weight() == sum(weights)
        assert global_fee_splitter.n_receivers() == 3


def test_set_multiple_receivers_exceeding_max_weight(global_fee_splitter, admin):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            global_fee_splitter.set_multiple_receivers(
                [(boa.env.generate_address(), 5001)]
            )


def test_remove_nonexistent_receiver(global_fee_splitter, admin):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            global_fee_splitter.remove_receiver(boa.env.generate_address())


def test_remove_middle_receiver(global_fee_splitter, admin, multiple_fee_receivers):
    receivers = multiple_fee_receivers[:3]
    weights = [1000, 1500, 2000]

    with boa.env.prank(admin.address):
        for i in range(3):
            global_fee_splitter.set_receiver(receivers[i], weights[i])

        global_fee_splitter.remove_receiver(receivers[1])
        assert global_fee_splitter.receiver_weights(receivers[1]) == 0
        assert global_fee_splitter.total_weight() == weights[0] + weights[2]
        assert global_fee_splitter.n_receivers() == 2

        assert global_fee_splitter.receivers(0) == receivers[0]
        assert global_fee_splitter.receivers(1) == receivers[2]


def test_remove_last_receiver(global_fee_splitter, admin, multiple_fee_receivers):
    receivers = multiple_fee_receivers[:3]
    weights = [1000, 1500, 2000]

    with boa.env.prank(admin.address):
        for i in range(3):
            global_fee_splitter.set_receiver(receivers[i], weights[i])

        global_fee_splitter.remove_receiver(receivers[2])
        assert global_fee_splitter.n_receivers() == 2
        assert global_fee_splitter.total_weight() == weights[0] + weights[1]


def test_remove_first_receiver(global_fee_splitter, admin, multiple_fee_receivers):
    receivers = multiple_fee_receivers[:3]
    weights = [1000, 1500, 2000]

    with boa.env.prank(admin.address):
        for i in range(3):
            global_fee_splitter.set_receiver(receivers[i], weights[i])

        global_fee_splitter.remove_receiver(receivers[0])
        assert global_fee_splitter.n_receivers() == 2
        assert global_fee_splitter.total_weight() == weights[1] + weights[2]

        assert global_fee_splitter.receivers(0) == receivers[2]
        assert global_fee_splitter.receivers(1) == receivers[1]


def test_max_receivers_limit_reached(global_fee_splitter, admin):
    with boa.env.prank(admin.address):
        for i in range(10):
            receiver = boa.env.generate_address()
            global_fee_splitter.set_receiver(receiver, 100)

        with pytest.raises(Exception):
            global_fee_splitter.set_receiver(boa.env.generate_address(), 100)


def test_max_receivers_remove_and_add(global_fee_splitter, admin):
    with boa.env.prank(admin.address):
        for i in range(10):
            receiver = boa.env.generate_address()
            global_fee_splitter.set_receiver(receiver, 100)

        global_fee_splitter.remove_receiver(global_fee_splitter.receivers(0))
        global_fee_splitter.set_receiver(boa.env.generate_address(), 100)
        assert global_fee_splitter.n_receivers() == 10


def test_distributor_weight_initial(global_fee_splitter):
    assert global_fee_splitter.distributor_weight() == 10000


def test_distributor_weight_with_receiver(global_fee_splitter, admin, fee_receiver):
    with boa.env.prank(admin.address):
        global_fee_splitter.set_receiver(fee_receiver, 2000)
        assert global_fee_splitter.distributor_weight() == 8000


def test_distributor_weight_update(global_fee_splitter, admin, fee_receiver):
    with boa.env.prank(admin.address):
        global_fee_splitter.set_receiver(fee_receiver, 2000)
        global_fee_splitter.set_receiver(fee_receiver, 3000)
        assert global_fee_splitter.distributor_weight() == 7000


def test_distributor_weight_after_remove(global_fee_splitter, admin, fee_receiver):
    with boa.env.prank(admin.address):
        global_fee_splitter.set_receiver(fee_receiver, 2000)
        global_fee_splitter.remove_receiver(fee_receiver)
        assert global_fee_splitter.distributor_weight() == 10000


def test_edge_case_max_weight(global_fee_splitter, admin, fee_receiver):
    with boa.env.prank(admin.address):
        global_fee_splitter.set_receiver(fee_receiver, 5000)
        assert global_fee_splitter.total_weight() == 5000
        assert global_fee_splitter.distributor_weight() == 5000
