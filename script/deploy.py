from moccasin.boa_tools import VyperContract
from moccasin.config import get_config

from script.utils.ipfs import pin_to_ipfs
from src import FeeAllocator
from tests.conftest import EMPTY_COMPENSATION

FEE_COLLECTOR = (
    get_config().get_active_network().manifest_named("fee_collector")
)
HOOKER = get_config().get_active_network().manifest_named("hooker")
FEE_DISTRIBUTOR = (
    get_config().get_active_network().manifest_named("fee_distributor")
)
CRVUSD = get_config().get_active_network().manifest_named("crvusd")
AGENT = get_config().get_active_network().manifest_named("agent")
VOTING = get_config().get_active_network().manifest_named("voting")
COMMUNITY_FUND = (
    get_config().get_active_network().manifest_named("community_fund")
)


def prepare_actions(fee_allocator):
    # 1. Set allocator as hook
    set_allocator_as_hook_calldata = HOOKER.set_hooks.prepare_calldata(
        [
            (
                fee_allocator.address,
                fee_allocator.distribute_fees.prepare_calldata(),
                EMPTY_COMPENSATION,
                True,
            )
        ]
    )
    # 2. Cancel previous distributor approval
    cancel_distributor_approval_calldata = (
        HOOKER.one_time_hooks.prepare_calldata(
            [
                (
                    CRVUSD.address,
                    CRVUSD.approve.prepare_calldata(
                        FEE_DISTRIBUTOR.address, 0
                    ),
                    EMPTY_COMPENSATION,
                    False,
                )
            ],
            [(0, 0, b"")],
        )
    )
    # 3. Approve allocator to spend hooker's crvUSD
    approve_allocator_for_crvusd_spend_calldata = (
        HOOKER.one_time_hooks.prepare_calldata(
            [
                (
                    CRVUSD.address,
                    CRVUSD.approve.prepare_calldata(
                        fee_allocator.address, 2**256 - 1
                    ),
                    EMPTY_COMPENSATION,
                    False,
                )
            ],
            [(0, 0, b"")],
        )
    )
    # 4. Set the community fund as a recipient for 10% of incoming fees
    create_community_fund_allocation_call_data = (
        fee_allocator.set_receiver.prepare_calldata(
            COMMUNITY_FUND.address, 1000
        )
    )
    return [
        (HOOKER.address, set_allocator_as_hook_calldata),
        (HOOKER.address, cancel_distributor_approval_calldata),
        (HOOKER.address, approve_allocator_for_crvusd_spend_calldata),
        (fee_allocator.address, create_community_fund_allocation_call_data),
    ]


def encode_call_script(actions):
    """
    Encodes multiple calls into an EVM script format.
    The format is: [spec_id][length][contract][calldata]...
    where spec_id = 0x00000001 for CALL scripts
    """
    script = b"\x00\x00\x00\x01"  # spec_id for CallsScript

    for target, calldata in actions:
        # Encode each action as: [20 bytes address][4 bytes calldataLength][calldata]
        calldata_length = len(calldata)
        script += bytes.fromhex(target[2:])
        script += calldata_length.to_bytes(4, "big")
        script += calldata

    return script


def deploy() -> (VyperContract, int, str, list):
    description = "Activate the fee allocator and redirect 10% of revenue to community fund - https://gov.curve.finance/t/activate-the-fee-allocator-and-redirect-10-of-revenue-to-community-fund/10676"  # noqa
    fee_allocator = FeeAllocator.deploy(
        FEE_DISTRIBUTOR,  # fee distributor
        FEE_COLLECTOR,  # fee collector
        AGENT,  # dao proxy
    )
    actions = prepare_actions(fee_allocator)
    agent_actions = []
    for target, calldata in actions:
        # Agent.execute(target, 0, calldata)
        agent_calldata = AGENT.execute.prepare_calldata(target, 0, calldata)
        agent_actions.append((AGENT.address, agent_calldata))
    execution_script = encode_call_script(agent_actions)
    metadata = pin_to_ipfs(description)
    proposal_id = VOTING.newVote(
        execution_script,
        metadata,
        False,  # cast_vote - automatically vote yes
        False,  # executes_if_decided - execute immediately if vote passes
    )
    return fee_allocator, proposal_id, metadata, VOTING.get_logs()


def construst():
    # If your contract constructor is: __init__(address fee_distributor, address fee_collector, address agent)
    fa = FeeAllocator.at("0x874942096Ed129C1a7c99de6C7Aa6fa0B679f322")
    result = get_config().get_active_network().moccasin_verify(fa)
    result.wait_for_verification()
    print(fa.hex())


def moccasin_main() -> VyperContract:
    return construst()
