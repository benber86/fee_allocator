# pragma version 0.4.0
# @license MIT

from ethereum.ercs import IERC20

from snekmate.auth import ownable

initializes: ownable
exports: (
    ownable.transfer_ownership,
    ownable.renounce_ownership,
    ownable.owner
)

event ReceiverSet:
    receiver: indexed(address)
    old_weight: uint256
    new_weight: uint256

event ReceiverRemoved:
    receiver: indexed(address)

MAX_RECEIVERS: constant(uint256) = 10
MAX_BPS: constant(uint256) = 10_000
MAX_TOTAL_WEIGHT: constant(uint256) = 5_000

crvusd: immutable(IERC20)
fee_distributor: public(immutable(address))

receiver_weights: public(HashMap[address, uint256])
receivers: public(DynArray[address, MAX_RECEIVERS])
receiver_indices: HashMap[address, uint256]

version: public(constant(String[8])) = "0.1.0"

@external
def __init__(
    _crvusd: IERC20,
    _fee_distributor: address,
    owner: address,):
    """
    @notice Initialize the contract with the fee distributor address
    @notice The fee distributor will receive whatever is not distributed to other receivers
    @param _fee_distributor The address of the fee distributor contract
    @param _crvusd The address of the crvUSD token contract
    """
    assert _crvusd.address != empty(address), "zeroaddr: crvusd"
    assert owner != empty(address), "zeroaddr: owner"

    ownable.__init__()
    ownable._transfer_ownership(owner)

    fee_distributor = _fee_distributor
    crvusd = _crvusd


@internal
@view
def _calculate_total_weight() -> uint256:
    """
    @dev Calculate the total weight of all receivers
    @return The total weight
    """
    total: uint256 = 0
    for receiver in self.receivers:
        total += self.receiver_weights[receiver]
    return total


@external
def set_receiver(receiver: address, weight: uint256):
    """
    @notice Add or update a receiver with a specified weight
    @param receiver The address of the receiver
    @param weight The weight assigned to the receiver
    """
    ownable._check_owner()
    assert receiver != empty(address), "zeroaddr: receiver"
    assert weight > 0, "receivers: invalid weight"

    old_weight: uint256 = self.receiver_weights[receiver]
    total_weight: uint256 = self._calculate_total_weight()

    if old_weight > 0:
        total_weight = total_weight - old_weight + weight
    else:
        assert len(self.receivers) < MAX_RECEIVERS, "receivers: max limit reached"
        total_weight += weight

    assert total_weight <= MAX_TOTAL_WEIGHT, "receivers: exceeds max total weight"

    if old_weight == 0:
        self.receiver_indices[receiver] = len(self.receivers)
        self.receivers.append(receiver)

    self.receiver_weights[receiver] = weight

    log ReceiverSet(receiver, old_weight, weight)


@external
def remove_receiver(receiver: address):
    """
    @notice Remove a receiver from the list
    @param receiver The address of the receiver to remove
    """
    ownable._check_owner()
    assert self.receiver_weights[receiver] > 0, "receivers: does not exist"

    index_to_remove: uint256 = self.receiver_indices[receiver]
    last_index: uint256 = len(self.receivers) - 1

    if index_to_remove != last_index:
        last_receiver: address = self.receivers[last_index]
        self.receivers[index_to_remove] = last_receiver
        self.receiver_indices[last_receiver] = index_to_remove

    self.receivers.pop()

    self.receiver_weights[receiver] = 0
    self.receiver_indices[receiver] = 0

    log ReceiverRemoved(receiver)


@view
@external
def n_receivers() -> uint256:
    """
    @notice Get the number of receivers
    @return The number of receivers
    """
    return len(self.receivers)


@view
@external
def distributor_weight() -> uint256:
    """
    @notice Get the portion of fees going to the fee distributor for veCRV
    @return The distributors' weight
    """
    return MAX_BPS - self._calculate_total_weight()


@view
@external
def get_all_receivers_with_weights() -> (DynArray[address, MAX_RECEIVERS], DynArray[uint256, MAX_RECEIVERS]):
    """
    @notice Get all receivers with their weights
    @return Tuple of (addresses array, weights array)
    """
    weights: DynArray[uint256, MAX_RECEIVERS] = []

    for receiver in self.receivers:
        weights.append(self.receiver_weights[receiver])

    return (self.receivers, weights)