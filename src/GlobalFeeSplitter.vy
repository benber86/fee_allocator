# pragma version 0.4.1
# @license MIT

from ethereum.ercs import IERC20

from snekmate.auth import ownable

initializes: ownable
exports: (ownable.transfer_ownership, ownable.renounce_ownership, ownable.owner)


interface FeeCollector:
    def hooker() -> address: view
    def owner() -> address: view


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

receiver_weights: public(HashMap[address, uint256])
receivers: public(DynArray[address, MAX_RECEIVERS])
receiver_indices: HashMap[address, uint256]
total_weight: public(uint256)

version: public(constant(String[8])) = "0.1.0"


@deploy
def __init__(
    _fee_distributor: FeeDistributor,
    _fee_collector: FeeCollector,
    owner: address,
):
    """
    @notice Initialize the contract with the fee distributor address
    @notice The fee distributor will receive whatever is not distributed to other receivers
    @param _fee_distributor The address of the fee distributor contract
    """
    assert owner != empty(address), "zeroaddr: owner"
    assert _fee_distributor.address != empty(
        address
    ), "zeroaddr: fee_distributor"
    assert _fee_collector.address != empty(address), "zeroaddr: fee_collector"

    ownable.__init__()
    ownable._transfer_ownership(owner)

    fee_distributor = _fee_distributor
    fee_collector = _fee_collector
    self.total_weight = 0


@internal
def _set_receiver(receiver: address, weight: uint256):
    """
    @notice Add or update a receiver with a specified weight
    @param receiver The address of the receiver
    @param weight The weight assigned to the receiver
    """
    ownable._check_owner()
    assert receiver != empty(address), "zeroaddr: receiver"
    assert weight > 0, "receivers: invalid weight, use remove_receiver"

    old_weight: uint256 = self.receiver_weights[receiver]
    new_total_weight: uint256 = self.total_weight

    if old_weight > 0:
        new_total_weight = new_total_weight - old_weight + weight
    else:
        assert (
            len(self.receivers) < MAX_RECEIVERS
        ), "receivers: max limit reached"
        new_total_weight += weight

    assert (
        new_total_weight <= MAX_TOTAL_WEIGHT
    ), "receivers: exceeds max total weight"

    if old_weight == 0:
        self.receiver_indices[receiver] = (
            len(self.receivers) + 1
        )  # offset by 1, 0 is for deleted receivers
        self.receivers.append(receiver)

    self.receiver_weights[receiver] = weight
    self.total_weight = new_total_weight  # Update the stored total weight

    log ReceiverSet(receiver=receiver, old_weight=old_weight, new_weight=weight)


@external
def set_receiver(receiver: address, weight: uint256):
    """
    @notice Add or update a receiver with a specified weight
    @param receiver The address of the receiver
    @param weight The weight assigned to the receiver
    """
    self._set_receiver(receiver, weight)


@external
def set_multiple_receivers(configs: DynArray[ReceiverConfig, MAX_RECEIVERS]):
    """
    @notice Add or update multiple receivers with specified weights
    @param configs Array of receiver configurations (address, weight)
    @dev When adding new receivers, if total weight might exceed MAX_TOTAL_WEIGHT,
         place receivers being updated with lower weights first in the array
    """
    assert len(configs) > 0, "receivers: empty array"

    for i: uint256 in range(MAX_RECEIVERS):
        if i >= len(configs):
            break

        config: ReceiverConfig = configs[i]
        self._set_receiver(config.receiver, config.weight)


@external
def remove_receiver(receiver: address):
    """
    @notice Remove a receiver from the list
    @param receiver The address of the receiver to remove
    """
    ownable._check_owner()
    weight: uint256 = self.receiver_weights[receiver]
    assert weight > 0, "receivers: does not exist"

    index_to_remove: uint256 = self.receiver_indices[receiver] - 1
    last_index: uint256 = len(self.receivers) - 1
    assert self.receivers[index_to_remove] == receiver
    if index_to_remove < last_index:
        last_receiver: address = self.receivers[last_index]
        self.receivers[index_to_remove] = last_receiver
        self.receiver_indices[last_receiver] = index_to_remove + 1

    self.receivers.pop()

    self.receiver_weights[receiver] = 0
    self.receiver_indices[receiver] = 0

    self.total_weight -= weight

    log ReceiverRemoved(receiver=receiver)


@nonreentrant
@external
def distribute_fees(_fee_token: address):
    """
    @notice Distribute accumulated crvUSD fees to receivers based on their weights
    @param _fee_token The address of the reward token contract (crvUSD)
    """
    assert msg.sender == staticcall fee_collector.hooker()
    fee_token: IERC20 = IERC20(_fee_token)
    amount_receivable: uint256 = staticcall fee_token.balanceOf(msg.sender)
    extcall fee_token.transferFrom(msg.sender, self, amount_receivable)
    balance: uint256 = staticcall fee_token.balanceOf(self)
    assert balance > 0, "receivers: no fees to distribute"

    remaining_balance: uint256 = balance

    for receiver: address in self.receivers:
        weight: uint256 = self.receiver_weights[receiver]
        amount: uint256 = balance * weight // MAX_BPS
        if amount > 0:
            extcall fee_token.transfer(receiver, amount)
            remaining_balance -= amount
    extcall fee_token.approve(fee_distributor.address, 0)
    extcall fee_token.approve(fee_distributor.address, remaining_balance)
    extcall fee_distributor.burn(fee_token.address)
    log FeesDistributed(
        total_amount=balance, distributor_share=remaining_balance
    )


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
    return MAX_BPS - self.total_weight
