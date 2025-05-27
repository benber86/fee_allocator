from src import GlobalFeeSplitter
from moccasin.boa_tools import VyperContract

def deploy() -> VyperContract:
    return GlobalFeeSplitter.deploy(
        "0xD16d5eC345Dd86Fb63C6a9C43c517210F1027914", # fee distributor
        "0xa2Bcd1a4Efbd04B63cd03f5aFf2561106ebCCE00", # fee collector
        "0x40907540d8a6C65c637785e8f8B742ae6b0b9968" # dao proxy
    )

def moccasin_main() -> VyperContract:
    return deploy()
