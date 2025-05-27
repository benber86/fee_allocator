# Curve Fee Allocator

## Overview

The FeeAllocator contract serves as an intermediary layer between the [`Hooker`](https://docs.curve.finance/fees/Hooker/) and [`FeeDistributor`](https://docs.curve.finance/fees/FeeDistributor/) which redistributes fees accrued by Curve to holders of the veCRV token.

It allows protocol fees to be split among multiple receivers before the remainder flows to veCRV holders. This allows the DAO to designate different avenues where a portion of fees can be redistributed, for instance to fund service providers such as Swiss Stake, or accumulate an insurance fund for bad debt.

The share of fees that can go to receivers is capped at 50%, meaning that half of protocol revenue will always flow back to veCRV. If the amount of fees redirected to receivers is lower than 50%, the remainder of fees will also flow to veCRV stakers.

A maximum of 10 receivers can be added.

## Architecture

![fee_allocation_diagram.png](fee_allocation_diagram.png)

## Workflow

### Current Workflow

Currently when calling `forward` on the [`FeeCollector`](https://etherscan.io/address/0xa2Bcd1a4Efbd04B63cd03f5aFf2561106ebCCE00) during the `FORWARD` period of the week, collected fees accumulated in the contract from the burning process are transferred to the `Hooker`. The `duty_act` function on the `Hooker` is called, executing the configured hook.

The `Hooker` on mainnet has one single hook targeting the `FeeDistributor` calling its `burn` function for the crvUSD token. The `burn` function in turn transfers the entire crvUSD balance from the caller (=`Hooker`) to itself and makes it available to veCRV holders. 

### Revised Workflow

The `FeeAllocator` contract is inserted in the current workflow by replacing the mainnet `Hooker`'s hook with one that calls `distribute_fees` on the `FeeAllocator` instead.

The `FeeAllocator` will transfer the `Hooker`'s crvUSD balance to itself, allocate the funds to each of the specified receivers according to their weight. Afterwards, it calls `burn` on the `FeeDistributor` which transfers the remaining balance to the `FeeDistributor` and makes it available to veCRV holders.

## Specifying Receivers

Receivers can be added via the `set_receiver` function by specifying the receiver's address and the percentage of the collected fees (in BPS) to direct towards it. For instance:

```
fee_allocator.set_receiver(grants_multisig, 1000)  # 10%
fee_allocator.set_receiver(dev_fund, 500)          # 5%
# Remaining 85% will go to veCRV holders
```

Receivers can only be added, modified or removed by the DAO. 