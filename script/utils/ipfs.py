# From: https://github.dev/mo-anon/curve-dao/blob/main/curve_dao/addresses.py
import requests
import os

PINATA_TOKEN = os.environ.get("PINATA_TOKEN")


def pin_to_ipfs(description: str):
    """Uploads vote description to IPFS via Pinata and returns the IPFS hash.

    NOTE: Needs environment variables for Pinata IPFS access. Please
    set up an IPFS project to generate API key and API secret!
    """

    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    headers = {
        "Authorization": f"Bearer {PINATA_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "pinataContent": {"text": description},
        "pinataMetadata": {"name": "pinnie.json"},
        "pinataOptions": {"cidVersion": 1},
    }

    response = requests.request("POST", url, json=payload, headers=headers)

    try:
        assert 200 <= response.status_code < 400
        ipfs_hash = response.json()["IpfsHash"]
        print(f"Pinned Vote description to ipfs:{ipfs_hash}")
        return ipfs_hash

    except Exception:
        print(f"POST to IPFS failed: {response.status_code}")
        raise
