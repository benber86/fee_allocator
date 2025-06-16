import boa
import pytest


def test_access_control_set_receiver(fee_allocator, admin, fee_receiver):
    random_address = boa.env.generate_address()

    with boa.env.prank(random_address):
        with pytest.raises(Exception):
            fee_allocator.set_receiver(fee_receiver, 1000)

    with boa.env.prank(admin.address):
        fee_allocator.set_receiver(fee_receiver, 1000)
        assert fee_allocator.receiver_weights(fee_receiver) == 1000


def test_access_control_set_multiple_receivers(fee_allocator, admin, fee_receiver):
    random_address = boa.env.generate_address()

    with boa.env.prank(random_address):
        with pytest.raises(Exception):
            fee_allocator.set_multiple_receivers([(fee_receiver, 1000)])

    with boa.env.prank(admin.address):
        fee_allocator.set_multiple_receivers([(fee_receiver, 1000)])
        assert fee_allocator.receiver_weights(fee_receiver) == 1000


def test_access_control_remove_receiver(fee_allocator, admin, fee_receiver):
    random_address = boa.env.generate_address()

    with boa.env.prank(admin.address):
        fee_allocator.set_receiver(fee_receiver, 1000)

    with boa.env.prank(random_address):
        with pytest.raises(Exception):
            fee_allocator.remove_receiver(fee_receiver)

    with boa.env.prank(admin.address):
        fee_allocator.remove_receiver(fee_receiver)
        assert fee_allocator.receiver_weights(fee_receiver) == 0


def test_access_control_transfer_ownership(fee_allocator, admin):
    random_address = boa.env.generate_address()
    new_owner = boa.env.generate_address()

    with boa.env.prank(random_address):
        with pytest.raises(Exception):
            fee_allocator.transfer_ownership(new_owner)

    with boa.env.prank(admin.address):
        fee_allocator.transfer_ownership(new_owner)
        assert fee_allocator.owner() == new_owner


def test_access_control_distribute_fees(fee_allocator, actual_crvusd, admin):
    random_address = boa.env.generate_address()

    with boa.env.prank(random_address):
        with pytest.raises(Exception):
            fee_allocator.distribute_fees()
