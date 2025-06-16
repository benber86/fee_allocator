import boa
from boa.contracts.abi.abi_contract import ABIContractFactory

from script.deploy import deploy
from tests.conftest import WEEK

CONVEX = "0x989AEb4d175e16225E39E87d0D97A3360524AD80"
STD = "0x52f541764E6e90eeBc5c21Ff570De0e2D63766B6"
MIN_VESTING_DURATION = 86400 * 365
VESTING_ESCROW_CLAIM_ABI = [
    {
        "name": "claim",
        "outputs": [],
        "inputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "name": "claim",
        "outputs": [],
        "inputs": [{"type": "address", "name": "addr"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


def test_deployment(
    admin,
    voting,
    community_fund,
    actual_fee_distributor,
    actual_fee_collector,
    actual_hooker,
    actual_crvusd,
    crvusd_minter,
    agent,
):
    # Test the deployment & vote creation
    fee_allocator, proposal_id, metadata, logs = deploy()
    assert voting.votesLength() == proposal_id + 1
    prop_details = voting.getVote(proposal_id)
    assert prop_details[0]  # open
    assert logs[0].metadata == metadata
    assert logs[0].voteId == proposal_id
    assert logs[0].creator == admin.address
    with boa.env.prank(STD):
        voting.votePct(proposal_id, int(1e18), 0, False)
    with boa.env.prank(CONVEX):
        voting.votePct(proposal_id, int(1e18), 0, False)
    boa.env.time_travel(seconds=WEEK)
    assert voting.canExecute(proposal_id)
    voting.executeVote(proposal_id)
    prop_details = voting.getVote(proposal_id)
    assert prop_details[1]  # executed
    assert fee_allocator.receiver_weights(community_fund.address) == 1_000

    # Test the distribution workflow
    pre_distribution_collector_balance = actual_crvusd.balanceOf(
        actual_fee_collector.address
    )
    pre_distribution_distributor_balance = actual_crvusd.balanceOf(
        actual_fee_distributor
    )
    pre_distribution_community_balance = actual_crvusd.balanceOf(
        community_fund.address
    )
    pre_distribution_caller_balance = actual_crvusd.balanceOf(admin)

    actual_fee_collector.forward([(0, 0, b"")], admin.address)

    post_distribution_collector_balance = actual_crvusd.balanceOf(
        actual_fee_collector.address
    )
    post_distribution_community_balance = actual_crvusd.balanceOf(
        community_fund.address
    )
    post_distribution_distributor_balance = actual_crvusd.balanceOf(
        actual_fee_distributor
    )
    post_distribution_caller_balance = actual_crvusd.balanceOf(admin)

    pre = {
        "collector": pre_distribution_collector_balance * 1e-18,
        "distributor": pre_distribution_distributor_balance * 1e-18,
        "community": pre_distribution_community_balance * 1e-18,
        "caller": pre_distribution_caller_balance * 1e-18,
    }
    post = {
        "collector": post_distribution_collector_balance * 1e-18,
        "distributor": post_distribution_distributor_balance * 1e-18,
        "community": post_distribution_community_balance * 1e-18,
        "caller": post_distribution_caller_balance * 1e-18,
    }

    def pct(x):
        return f"{100 * x:.2f}%"

    pre_collector = float(pre["collector"])
    table = []
    for k in pre:
        delta = float(post[k]) - float(pre[k])
        perc = delta / pre_collector if pre_collector else 0
        table.append((k, float(pre[k]), float(post[k]), delta, perc))

    header = ["Account", "Pre", "Post", "Delta", "Delta (% of pre_collector)"]
    print(
        f"{header[0]:<12} {header[1]:>10} {header[2]:>10} {header[3]:>10} {header[4]:>18}"
    )
    for row in table:
        print(
            f"{row[0]:<12} {row[1]:>10.2f} {row[2]:>10.2f} {row[3]:>10.2f} {pct(row[4]):>18}"
        )

    assert abs(table[2][4] - 0.10) < 0.01  # 10% goes to community fund ±1%

    # Test that we can create a vest from the community fund using crvusd
    grantee = boa.env.generate_address()
    with boa.env.prank(agent.address):
        vesting_contract_address = community_fund.deploy_vesting_contract(
            actual_crvusd.address,
            grantee,
            post_distribution_community_balance,
            False,
            MIN_VESTING_DURATION,
        )

    boa.env.time_travel(seconds=MIN_VESTING_DURATION + 1)

    vesting_contract = ABIContractFactory(
        "Vesting", VESTING_ESCROW_CLAIM_ABI
    ).at(vesting_contract_address)
    vesting_contract.claim(grantee)
    assert (
        actual_crvusd.balanceOf(grantee) == post_distribution_community_balance
    )
