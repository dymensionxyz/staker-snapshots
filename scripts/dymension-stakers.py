import subprocess
import json
from datetime import datetime

# change accordingly, and it is recommended to use your personal RPC
binary="./dymd"
rpc="https://rpc.cosmos.directory:443/dymension"

def atto_to_none(atto):
    """Convert from atto"""
    return float(atto / (10**18))

def run_command(command):
    result = subprocess.run(command.split(), capture_output=True, text=True)
    if result.stderr:
        print("Error:", result.stderr.strip())
        return None
    else:
        return result.stdout.strip()

def fetch_delegations(validator_address):
    delegations = []
    offset = 0
    limit = 1000  # Fetch 1000 delegations at a time

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

    if len(delegations) != total_delegator:
        print(f"We didn't capture all delegators. Total is {total_delegator} vs {len(delegations)}")
        exit(1)
    return delegations

# Retrieve Validators and delegators
delegator_stakes={}
validators_output = run_command(f"{binary} q staking validators -o json --node {rpc}")
if validators_output:
    validators_data = json.loads(validators_output)
    validator_addresses = [validator["operator_address"] for validator in validators_data["validators"]]
    for validator_address in validator_addresses:
        delegators_data = fetch_delegations(validator_address)
        for delegations in delegators_data:
            # first time adding the delegator to the dictionnary
            if delegator_stakes.get(delegations["delegation"]["delegator_address"]) is None:
                delegator_stakes[delegations["delegation"]["delegator_address"]] = 0
            delegator_stakes[delegations["delegation"]["delegator_address"]] += atto_to_none(float(delegations["balance"]["amount"]))

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
        file.write(f"{delegator}: {delegator_stakes[delegator]}\n")
