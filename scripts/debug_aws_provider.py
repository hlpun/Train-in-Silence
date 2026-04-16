import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import vcr
from tis.planner.market.providers import AWSProvider
from tis.planner.models import Constraints

def run_debug():
    # Use the cassette we just created
    my_vcr = vcr.VCR(
        cassette_library_dir='tests/cassettes/test_networking',
        record_mode='none', # Force use of cassette
    )
    
    with my_vcr.use_cassette('test_aws_public_price_list_fetch.yaml'):
        provider = AWSProvider()
        constraints = Constraints(platforms=["aws"], region=["us-east-1"], max_gpus=1)
        result = provider.fetch(constraints)
        
        print(f"Status OK: {result.status.ok}")
        print(f"Offers count: {len(result.offers)}")
        print(f"Message: {result.status.message}")
        if result.offers:
            print(f"First offer: {result.offers[0]}")
        else:
            print("No offers found.")

if __name__ == "__main__":
    run_debug()
