import boa
import pytest


def test_access_control_set_receiver(global_fee_splitter, admin, fee_receiver):
    random_address = boa.env.generate_address()

    with boa.env.prank(random_address):
        with pytest.raises(Exception):
            global_fee_splitter.set_receiver(fee_receiver, 1000)

    with boa.env.prank(admin.address):
        global_fee_splitter.set_receiver(fee_receiver, 1000)
        assert global_fee_splitter.receiver_weights(fee_receiver) == 1000


def test_access_control_set_multiple_receivers(global_fee_splitter, admin, fee_receiver):
    random_address = boa.env.generate_address()

    with boa.env.prank(random_address):
        with pytest.raises(Exception):
            global_fee_splitter.set_multiple_receivers([(fee_receiver, 1000)])

    with boa.env.prank(admin.address):
        global_fee_splitter.set_multiple_receivers([(fee_receiver, 1000)])
        assert global_fee_splitter.receiver_weights(fee_receiver) == 1000


def test_access_control_remove_receiver(global_fee_splitter, admin, fee_receiver):
    random_address = boa.env.generate_address()

    with boa.env.prank(admin.address):
        global_fee_splitter.set_receiver(fee_receiver, 1000)

    with boa.env.prank(random_address):
        with pytest.raises(Exception):
            global_fee_splitter.remove_receiver(fee_receiver)

    with boa.env.prank(admin.address):
        global_fee_splitter.remove_receiver(fee_receiver)
        assert global_fee_splitter.receiver_weights(fee_receiver) == 0


def test_access_control_transfer_ownership(global_fee_splitter, admin):
    random_address = boa.env.generate_address()
    new_owner = boa.env.generate_address()

    with boa.env.prank(random_address):
        with pytest.raises(Exception):
            global_fee_splitter.transfer_ownership(new_owner)

    with boa.env.prank(admin.address):
        global_fee_splitter.transfer_ownership(new_owner)
        assert global_fee_splitter.owner() == new_owner