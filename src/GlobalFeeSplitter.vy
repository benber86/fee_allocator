# pragma version 0.4.1
# @license MIT

from ethereum.ercs import IERC20

from snekmate.auth import ownable

initializes: ownable
exports: (
    ownable.transfer_ownership,
    ownable.renounce_ownership,
    ownable.owner
)

interface FeeDistributor:
    def burn(_coin: address) -> bool: nonpayable

event ReceiverSet:
    receiver: indexed(address)
    old_weight: uint256
    new_weight: uint256
    hook_foreplay: Bytes[1024]

event ReceiverRemoved:
    receiver: indexed(address)

event HookExecuted:
    receiver: indexed(address)
    value: uint256

struct HookInput:
    receiver_index: uint8
    value: uint256
    data: Bytes[8192]

struct ReceiverData:
    weight: uint256
    hook_foreplay: Bytes[1024]

MAX_RECEIVERS: constant(uint256) = 10
MAX_BPS: constant(uint256) = 10_000
MAX_TOTAL_WEIGHT: constant(uint256) = 5_000

crvusd: immutable(IERC20)
fee_distributor: public(immutable(FeeDistributor))

receiver_data: public(HashMap[address, ReceiverData])
receivers: public(DynArray[address, MAX_RECEIVERS])
receiver_indices: HashMap[address, uint256]

version: public(constant(String[8])) = "0.1.0"

@deploy
def __init__(
    _crvusd: IERC20,
    _fee_distributor: FeeDistributor,
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
    @dev Calculate the total weight of all receivers except the fee distributor
    @return The total weight
    """
    total: uint256 = 0
    for receiver: address in self.receivers:
        total += self.receiver_data[receiver].weight
    return total


@external
def set_receiver(receiver: address, weight: uint256, hook_foreplay: Bytes[1024]):
    """
    @notice Add or update a receiver with a specified weight and optional hook foreplay
    @param receiver The address of the receiver
    @param weight The weight assigned to the receiver
    @param hook_foreplay The hook foreplay data (method_id + fixed params)
    """
    ownable._check_owner()
    assert receiver != empty(address), "zeroaddr: receiver"
    assert weight > 0, "receivers: invalid weight"

    old_data: ReceiverData = self.receiver_data[receiver]
    old_weight: uint256 = old_data.weight
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

    self.receiver_data[receiver] = ReceiverData(
        weight=weight,
        hook_foreplay=hook_foreplay
    )

    log ReceiverSet(receiver=receiver, old_weight=old_weight, new_weight=weight, hook_foreplay=hook_foreplay)


@external
def remove_receiver(receiver: address):
    """
    @notice Remove a receiver from the list
    @param receiver The address of the receiver to remove
    """
    ownable._check_owner()
    assert self.receiver_data[receiver].weight > 0, "receivers: does not exist"

    index_to_remove: uint256 = self.receiver_indices[receiver]
    last_index: uint256 = len(self.receivers) - 1

    if index_to_remove != last_index:
        last_receiver: address = self.receivers[last_index]
        self.receivers[index_to_remove] = last_receiver
        self.receiver_indices[last_receiver] = index_to_remove

    self.receivers.pop()

    self.receiver_data[receiver] = empty(ReceiverData)
    self.receiver_indices[receiver] = 0

    log ReceiverRemoved(receiver=receiver)


@external
def distribute_fees(hook_inputs: DynArray[HookInput, MAX_RECEIVERS]):
    """
    @notice Distribute accumulated crvUSD fees to receivers based on their weights
    @param hook_inputs Array of hook inputs for each receiver to execute
    """
    ownable._check_owner()
    assert len(hook_inputs) == len(self.receivers), "receivers: missing hook input data"

    amount_receivable: uint256 = staticcall crvusd.balanceOf(msg.sender)
    extcall crvusd.transferFrom(msg.sender, self, amount_receivable)
    balance: uint256 = staticcall crvusd.balanceOf(self)
    assert balance > 0, "receivers: no fees to distribute"

    total_weight: uint256 = self._calculate_total_weight()
    distributor_weight: uint256 = MAX_BPS - total_weight

    i: uint256 = 0
    for receiver: address in self.receivers:
        weight: uint256 = self.receiver_data[receiver].weight
        amount: uint256 = balance * weight // MAX_BPS
        hook_foreplay: Bytes[1024] = self.receiver_data[receiver].hook_foreplay
        input: HookInput = hook_inputs[i]
        i+=1

        if len(hook_foreplay) == 0:
            extcall crvusd.transfer(receiver, amount)
        else:
            raw_call(
                receiver,
                concat(hook_foreplay, input.data),
                value=input.value,
                revert_on_failure=True
            )

            log HookExecuted(receiver=receiver, value=input.value)

    extcall fee_distributor.burn(crvusd.address)


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
def get_receiver_info(receiver: address) -> (uint256, Bytes[1024], bool):
    """
    @notice Get all information for a specific receiver
    @param receiver The address of the receiver
    @return A tuple containing (weight, hook_foreplay, exists)
    """
    data: ReceiverData = self.receiver_data[receiver]
    exists: bool = data.weight > 0
    return (data.weight, data.hook_foreplay, exists)