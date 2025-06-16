import boa
import pytest

from tests.conftest import ZERO_ADDRESS


def test_set_receiver_zero_address(fee_allocator, admin):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            fee_allocator.set_receiver(ZERO_ADDRESS, 1000)


def test_set_receiver_zero_weight(fee_allocator, admin, fee_receiver):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            fee_allocator.set_receiver(fee_receiver, 0)


def test_set_receiver_exceeding_max_weight(fee_allocator, admin, fee_receiver):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            fee_allocator.set_receiver(fee_receiver, 5001)


def test_set_receiver_valid(fee_allocator, admin, fee_receiver):
    with boa.env.prank(admin.address):
        fee_allocator.set_receiver(fee_receiver, 1000)
        assert fee_allocator.receiver_weights(fee_receiver) == 1000
        assert fee_allocator.total_weight() == 1000


def test_update_receiver_weight(fee_allocator, admin, fee_receiver):
    with boa.env.prank(admin.address):
        fee_allocator.set_receiver(fee_receiver, 1000)
        fee_allocator.set_receiver(fee_receiver, 2000)
        assert fee_allocator.receiver_weights(fee_receiver) == 2000
        assert fee_allocator.total_weight() == 2000


def test_set_multiple_receivers_empty_array(fee_allocator, admin):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            fee_allocator.set_multiple_receivers([])


def test_set_multiple_receivers_valid(
    fee_allocator, admin, multiple_fee_receivers
):
    with boa.env.prank(admin.address):
        receivers = multiple_fee_receivers[:3]
        weights = [1000, 1500, 2000]
        configs = [(receivers[i], weights[i]) for i in range(3)]

        fee_allocator.set_multiple_receivers(configs)

        for i in range(3):
            assert fee_allocator.receiver_weights(receivers[i]) == weights[i]

        assert fee_allocator.total_weight() == sum(weights)
        assert fee_allocator.n_receivers() == 3


def test_set_multiple_receivers_exceeding_max_weight(fee_allocator, admin):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            fee_allocator.set_multiple_receivers(
                [(boa.env.generate_address(), 5001)]
            )


def test_remove_nonexistent_receiver(fee_allocator, admin):
    with boa.env.prank(admin.address):
        with pytest.raises(Exception):
            fee_allocator.remove_receiver(boa.env.generate_address())


def test_remove_middle_receiver(fee_allocator, admin, multiple_fee_receivers):
    receivers = multiple_fee_receivers[:3]
    weights = [1000, 1500, 2000]

    with boa.env.prank(admin.address):
        for i in range(3):
            fee_allocator.set_receiver(receivers[i], weights[i])

        fee_allocator.remove_receiver(receivers[1])
        assert fee_allocator.receiver_weights(receivers[1]) == 0
        assert fee_allocator.total_weight() == weights[0] + weights[2]
        assert fee_allocator.n_receivers() == 2

        assert fee_allocator.receivers(0) == receivers[0]
        assert fee_allocator.receivers(1) == receivers[2]


def test_remove_last_receiver(fee_allocator, admin, multiple_fee_receivers):
    receivers = multiple_fee_receivers[:3]
    weights = [1000, 1500, 2000]

    with boa.env.prank(admin.address):
        for i in range(3):
            fee_allocator.set_receiver(receivers[i], weights[i])

        fee_allocator.remove_receiver(receivers[2])
        assert fee_allocator.n_receivers() == 2
        assert fee_allocator.total_weight() == weights[0] + weights[1]


def test_remove_first_receiver(fee_allocator, admin, multiple_fee_receivers):
    receivers = multiple_fee_receivers[:3]
    weights = [1000, 1500, 2000]

    with boa.env.prank(admin.address):
        for i in range(3):
            fee_allocator.set_receiver(receivers[i], weights[i])

        fee_allocator.remove_receiver(receivers[0])
        assert fee_allocator.n_receivers() == 2
        assert fee_allocator.total_weight() == weights[1] + weights[2]

        assert fee_allocator.receivers(0) == receivers[2]
        assert fee_allocator.receivers(1) == receivers[1]


def test_add_remove_all_then_add_new(fee_allocator, admin, multiple_fee_receivers):
    receivers = multiple_fee_receivers[:5]
    weights = [1000, 1200, 800, 500, 1500]

    with boa.env.prank(admin.address):
        for i in range(5):
            fee_allocator.set_receiver(receivers[i], weights[i])

        assert fee_allocator.n_receivers() == 5
        assert fee_allocator.total_weight() == sum(weights)

        for _ in range(5):
            receiver_to_remove = fee_allocator.receivers(0)
            fee_allocator.remove_receiver(receiver_to_remove)

        assert fee_allocator.n_receivers() == 0
        assert fee_allocator.total_weight() == 0
        assert fee_allocator.distributor_weight() == 10000

        new_receivers = multiple_fee_receivers[5:8]
        new_weights = [700, 900, 1100]

        for i in range(3):
            fee_allocator.set_receiver(new_receivers[i], new_weights[i])

        assert fee_allocator.n_receivers() == 3
        assert fee_allocator.total_weight() == sum(new_weights)

        for i in range(3):
            assert fee_allocator.receiver_weights(new_receivers[i]) == new_weights[i]
            assert fee_allocator.receivers(i) == new_receivers[i]


def test_max_receivers_limit_reached(fee_allocator, admin):
    with boa.env.prank(admin.address):
        for i in range(10):
            receiver = boa.env.generate_address()
            fee_allocator.set_receiver(receiver, 100)

        with pytest.raises(Exception):
            fee_allocator.set_receiver(boa.env.generate_address(), 100)


def test_max_receivers_remove_and_add(fee_allocator, admin):
    with boa.env.prank(admin.address):
        for i in range(10):
            receiver = boa.env.generate_address()
            fee_allocator.set_receiver(receiver, 100)

        fee_allocator.remove_receiver(fee_allocator.receivers(0))
        fee_allocator.set_receiver(boa.env.generate_address(), 100)
        assert fee_allocator.n_receivers() == 10


def test_distributor_weight_initial(fee_allocator):
    assert fee_allocator.distributor_weight() == 10000


def test_distributor_weight_with_receiver(fee_allocator, admin, fee_receiver):
    with boa.env.prank(admin.address):
        fee_allocator.set_receiver(fee_receiver, 2000)
        assert fee_allocator.distributor_weight() == 8000


def test_distributor_weight_update(fee_allocator, admin, fee_receiver):
    with boa.env.prank(admin.address):
        fee_allocator.set_receiver(fee_receiver, 2000)
        fee_allocator.set_receiver(fee_receiver, 3000)
        assert fee_allocator.distributor_weight() == 7000


def test_distributor_weight_after_remove(fee_allocator, admin, fee_receiver):
    with boa.env.prank(admin.address):
        fee_allocator.set_receiver(fee_receiver, 2000)
        fee_allocator.remove_receiver(fee_receiver)
        assert fee_allocator.distributor_weight() == 10000


def test_edge_case_max_weight(fee_allocator, admin, fee_receiver):
    with boa.env.prank(admin.address):
        fee_allocator.set_receiver(fee_receiver, 5000)
        assert fee_allocator.total_weight() == 5000
        assert fee_allocator.distributor_weight() == 5000
