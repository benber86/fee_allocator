# pragma version ^0.4.1
"""
@title FeeAllocator
@license MIT
@author Curve Finance
@notice Allocate protocol fees between different receivers
"""

from ethereum.ercs import IERC20

from snekmate.auth import ownable

initializes: ownable
exports: (ownable.transfer_ownership, ownable.owner)


interface FeeCollector:
    def hooker() -> address: view
    def target() -> address: view


interface FeeDistributor:
    def burn(_coin: address) -> bool: nonpayable


event ReceiverSet:
    receiver: indexed(address)
    old_weight: uint256
    new_weight: uint256


event ReceiverRemoved:
    receiver: indexed(address)


event FeesDistributed:
    total_amount: uint256
    distributor_share: uint256


struct ReceiverConfig:
    receiver: address
    weight: uint256


MAX_RECEIVERS: public(constant(uint256)) = 10
MAX_BPS: constant(uint256) = 10_000
MAX_TOTAL_WEIGHT: public(constant(uint256)) = 5_000  # in bps

fee_distributor: public(immutable(FeeDistributor))
fee_collector: public(immutable(FeeCollector))
fee_token: public(immutable(IERC20))

receiver_weights: public(HashMap[address, uint256])
receivers: public(DynArray[address, MAX_RECEIVERS])
receiver_indices: HashMap[address, uint256]
total_weight: public(uint256)

VERSION: public(constant(String[8])) = "0.1.0"


@deploy
def __init__(
    _fee_distributor: FeeDistributor,
    _fee_collector: FeeCollector,
    _owner: address,
):
    """
    @notice Initialize the contract with the fee distributor address
    @notice The fee distributor will receive whatever is not distributed to other receivers
    @param _fee_distributor The address of the fee distributor contract
    @param _fee_collector The address of the fee collector contract
    @param _owner The address of the contract's owner
    """
    assert _owner != empty(address), "zeroaddr: owner"
    assert _fee_distributor.address != empty(address), "zeroaddr: fee_distributor"
    assert _fee_collector.address != empty(address), "zeroaddr: fee_collector"

    ownable.__init__()
    ownable._transfer_ownership(_owner)

    fee_distributor = _fee_distributor
    fee_collector = _fee_collector
    # the distributor only handles crvusd so any change of target token would imply a change
    # of distributor (and necessitate a redeploy)
    fee_token = IERC20(staticcall fee_collector.target())
    extcall fee_token.approve(
        fee_distributor.address, max_value(uint256), default_return_value=True
    )


@internal
def _set_receiver(_receiver: address, _weight: uint256):
    """
    @notice Add or update a receiver with a specified weight
    @param _receiver The address of the receiver
    @param _weight The weight assigned to the receiver
    """
    ownable._check_owner()
    assert _receiver != empty(address), "zeroaddr: receiver"
    assert _weight > 0, "receivers: invalid weight, use remove_receiver"

    old_weight: uint256 = self.receiver_weights[_receiver]
    new_total_weight: uint256 = self.total_weight

    if old_weight > 0:
        new_total_weight = new_total_weight - old_weight + _weight
    else:
        assert (len(self.receivers) < MAX_RECEIVERS), "receivers: max limit reached"
        new_total_weight += _weight

    assert (new_total_weight <= MAX_TOTAL_WEIGHT), "receivers: exceeds max total weight"

    if old_weight == 0:
        self.receiver_indices[_receiver] = (
            len(self.receivers) + 1
        )  # offset by 1, 0 is for deleted receivers
        self.receivers.append(_receiver)

    self.receiver_weights[_receiver] = _weight
    self.total_weight = new_total_weight  # Update the stored total weight

    log ReceiverSet(receiver=_receiver, old_weight=old_weight, new_weight=_weight)


@external
def set_receiver(_receiver: address, _weight: uint256):
    """
    @notice Add or update a receiver with a specified weight
    @param _receiver The address of the receiver
    @param _weight The weight assigned to the receiver
    """
    self._set_receiver(_receiver, _weight)


@external
def set_multiple_receivers(_configs: DynArray[ReceiverConfig, MAX_RECEIVERS]):
    """
    @notice Add or update multiple receivers with specified weights
    @param _configs Array of receiver configurations (address, weight)
    @dev When adding new receivers, if total weight might exceed MAX_TOTAL_WEIGHT,
         place receivers being updated with lower weights first in the array
    """
    assert len(_configs) > 0, "receivers: empty array"

    for i: uint256 in range(MAX_RECEIVERS):
        if i >= len(_configs):
            break

        config: ReceiverConfig = _configs[i]
        self._set_receiver(config.receiver, config.weight)


@external
def remove_receiver(_receiver: address):
    """
    @notice Remove a receiver from the list
    @param _receiver The address of the receiver to remove
    """
    ownable._check_owner()
    weight: uint256 = self.receiver_weights[_receiver]
    assert weight > 0, "receivers: does not exist"

    index_to_remove: uint256 = self.receiver_indices[_receiver] - 1
    last_index: uint256 = len(self.receivers) - 1
    assert self.receivers[index_to_remove] == _receiver
    if index_to_remove < last_index:
        last_receiver: address = self.receivers[last_index]
        self.receivers[index_to_remove] = last_receiver
        self.receiver_indices[last_receiver] = index_to_remove + 1

    self.receivers.pop()

    self.receiver_weights[_receiver] = 0
    self.receiver_indices[_receiver] = 0

    self.total_weight -= weight

    log ReceiverRemoved(receiver=_receiver)


@external
@nonreentrant
def distribute_fees():
    """
    @notice Distribute accumulated crvUSD fees to receivers based on their weights
    """
    assert (msg.sender == staticcall fee_collector.hooker()), "distribute: hooker only"

    amount_receivable: uint256 = staticcall fee_token.balanceOf(msg.sender)
    extcall fee_token.transferFrom(msg.sender, self, amount_receivable)
    balance: uint256 = staticcall fee_token.balanceOf(self)
    assert balance > 0, "receivers: no fees to distribute"

    remaining_balance: uint256 = balance

    for receiver: address in self.receivers:
        weight: uint256 = self.receiver_weights[receiver]
        amount: uint256 = balance * weight // MAX_BPS
        if amount > 0:
            extcall fee_token.transfer(receiver, amount, default_return_value=True)
            remaining_balance -= amount
    extcall fee_distributor.burn(fee_token.address)
    log FeesDistributed(total_amount=balance, distributor_share=remaining_balance)


@external
@view
def n_receivers() -> uint256:
    """
    @notice Get the number of receivers
    @return The number of receivers
    """
    return len(self.receivers)


@external
@view
def distributor_weight() -> uint256:
    """
    @notice Get the portion of fees going to the fee distributor for veCRV
    @return The distributors' weight
    """
    return MAX_BPS - self.total_weight
