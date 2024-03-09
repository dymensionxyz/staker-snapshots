import subprocess
import json
from datetime import datetime
import bech32
import binascii
import time
# change accordingly, and it is recommended to use your personal RPC
binary="dymd"
rpc="tcp://127.0.0.1:26657"

def atto_to_none(atto):
    """Convert from atto"""
    return float(atto / (10**18))

def dym_to_0x(address):
    b = bech32.bech32_decode(address)[1]
    b = bech32.convertbits(b, 5, 8, False)
    b = binascii.hexlify(bytearray(b)).decode('ascii')

    return f"0x{b}"

def run_command(command):
    result = subprocess.run(command.split(), capture_output=True, text=True)
    if result.stderr:
        print("Error:", result.stderr.strip())
        return None
    else:
        return result.stdout.strip()

def fetch_validators():
    validators = []
    offset = 0
    limit = 100  # Fetch 100 validators at a time

    # First query 1 validator and get the total size of delegator
    command = f"{binary} q staking validators -o json --count-total --limit 1 --node {rpc}"
    validator_data = json.loads(run_command(command))
    total_validator = int(validator_data["pagination"].get("total"))

    print(f"Network has a total of {total_validator} validators")

    while True:
        command = f"{binary} q staking validators -o json --limit {limit} --offset {offset} --node {rpc}"
        validator_output = run_command(command)
        if not validator_output:
            return None
        validators_data = json.loads(validator_output)
        validators.extend(validators_data["validators"])
        offset += limit  # Increment offset by the limit for the next chunk
        if offset >= total_validator:
            break

    if len(validators) != total_validator:
        print(f"We didn't capture all validators. Total is {total_validator} vs {len(validators)}")
        exit(1)
    return validators

def fetch_delegations(validator_address):
    delegations = []
    offset = 0
    limit = 5000  # Fetch 5000 delegations at a time

    # First query 1 delegator and get the total size of delegator
    command = f"{binary} q staking delegations-to {validator_address} -o json --count-total --limit 1 --node {rpc}"
    delegators_output = run_command(command)
    delegators_data = json.loads(delegators_output)
    total_delegator = int(delegators_data["pagination"].get("total"))
    print(f"{validator_address} has {total_delegator} delegators")

    while True:
        command = f"{binary} q staking delegations-to {validator_address} -o json --limit {limit} --offset {offset} --node {rpc}"
        delegators_output = run_command(command)
        if not delegators_output:
            return None
        delegators_data = json.loads(delegators_output)
        delegations.extend(delegators_data["delegation_responses"])
        offset += limit  # Increment offset by the limit for the next chunk
        if offset >= total_delegator:
            break

    if len(delegations) < total_delegator:
        # we may have more delegations
        error_message = f"We didn't capture all delegators. Total is {total_delegator} is above {len(delegations)}"
        raise RuntimeError(error_message)
    return delegations


def fetch_delegations_with_retry(validator_address):
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5
    retries = 0
    while retries < MAX_RETRIES:
        try:
            delegators_data = fetch_delegations(validator_address)
            if delegators_data is not None:
                return delegators_data
            else:
                print("Received None from fetch_delegations. Retrying...")
        except RuntimeError as e:
            print(f"Error fetching delegations: {e}. Retrying... (Attempt {retries + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY_SECONDS)
            retries += 1
        except Exception as e:
            print(f"An error occurred: {e} Retrying... (Attempt {retries + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY_SECONDS)
            retries += 1
    print(f"Max retries reached. Failed to fetch delegations after {MAX_RETRIES} attempts.")
    exit(1)

# Retrieve Validators and delegators
delegator_stakes = {}
delegator_stakes_from_active_validators_only = {}
validators_data = fetch_validators()
#print(validators_data)
if validators_data:
    validator_addresses = [validator["operator_address"] for validator in validators_data]
    active_validator_address_only = [validator["operator_address"] for validator in validators_data if validator["status"] == "BOND_STATUS_BONDED"]
    for validator_address in validator_addresses:
        delegators_data = fetch_delegations_with_retry(validator_address)
        for delegations in delegators_data:
            # first time adding the delegator to the dictionnary
            if delegator_stakes.get(delegations["delegation"]["delegator_address"]) is None:
                delegator_stakes[delegations["delegation"]["delegator_address"]] = 0
            if delegator_stakes_from_active_validators_only.get(delegations["delegation"]["delegator_address"]) is None:
                delegator_stakes_from_active_validators_only[delegations["delegation"]["delegator_address"]] = 0
            delegator_stakes[delegations["delegation"]["delegator_address"]] += atto_to_none(float(delegations["balance"]["amount"]))
            if validator_address in active_validator_address_only: # add only the delegation from active validator
                delegator_stakes_from_active_validators_only[delegations["delegation"]["delegator_address"]] += atto_to_none(float(delegations["balance"]["amount"]))
else:
    print(f"Error with : {binary} q staking validators -o json --node {rpc}")
    exit(1)

# Get Latest Block
status_output = run_command(f"{binary} status --node {rpc}")
if status_output:
    status_data = json.loads(status_output)
    snapshot_block = int(status_data["SyncInfo"]["latest_block_height"])
else:
    print("Error getting latest block")
    exit(1)

final_result = {
   "snapshot_block": snapshot_block,
   "delegators": delegator_stakes
}
#print(json.dumps(final_result))
print("write file following expected format")
# write file following expected format
today = datetime.now().strftime("%Y%m%d")
with open(f"pops_{today}.csv", 'w', newline='') as file:
    for delegator in delegator_stakes:
        file.write(f"{dym_to_0x(delegator)}, {delegator}, {delegator_stakes[delegator]}\n")

with open(f"pops_{today}-activeonly.csv", 'w', newline='') as file:
    for delegator in delegator_stakes_from_active_validators_only:
        if float(delegator_stakes_from_active_validators_only[delegator]) > 0:
            file.write(f"{dym_to_0x(delegator)}, {delegator}, {delegator_stakes_from_active_validators_only[delegator]}\n")