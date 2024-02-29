// Required npm packages:
// - util: Built-in Node.js module, no need to install separately.
// - child_process: Built-in Node.js module, no need to install separately.
// - bech32-converting: Install with `npm install bech32-converting`
// - fs: Built-in Node.js module, no need to install separately.

const util = require('node:util');
const exec = util.promisify(require('node:child_process').exec);
const converter = require("bech32-converting");
const fs = require('fs');

/**
 * Converts a DYM address to a hexadecimal address.
 * @param {string} dym_addr - The DYM address to convert.
 * @returns {string} The hexadecimal representation of the DYM address.
 */
function convertToHex(dym_addr) {
    try {
        return converter('dym').toHex(dym_addr);
    } catch (error) {
        console.error(`Failed to convert DYM address to hexadecimal: ${error}`);
        return null;
    }
}

/**
 * Fetches the list of delegators for a given validator address.
 * @param {string} v_addr - The validator address.
 * @param {Object} delegators - The object to store the delegators and their shares.
 */
async function fetchDelegators(v_addr, delegators) {
    let offset = 0;
    const pageSize = 3000;
    while (true) {
        let cmd = `dymd query staking delegations-to ${v_addr} --limit ${pageSize} --offset ${offset} -o json`;
        try {
            const { stdout, stderr } = await exec(cmd);
            if (stderr) {
                throw new Error(stderr);
            }

            const delegatorResponse = JSON.parse(stdout);
            const responses = delegatorResponse?.delegation_responses;

            for (const res of responses) {
                if (!res?.delegation?.delegator_address) continue;
                const d_addr = res?.delegation?.delegator_address;

                // Convert shares from adym to dym
                const shares = parseFloat(res.delegation.shares) / 1e18;

                delegators[d_addr] = delegators[d_addr] ? delegators[d_addr] + shares : shares;
            }

            if (responses.length < pageSize) {
                break;  // last Page, exit the loop
            }

            offset += responses.length;  // Increase the offset for the next iteration
        } catch (error) {
            console.error(`Failed to fetch delegators for validator ${v_addr}: ${error}`);
            break;
        }
    }
}

/**
 * Fetches the list of validator addresses.
 * @returns {Array} The list of validator addresses.
 */
async function fetchValidators() {
    try {
        const { stdout, stderr } = await exec('dymd query staking validators --limit 500 -o json');
        if (stderr) {
            throw new Error(stderr);
        }

        const validatorsResponse = JSON.parse(stdout);
        const validators = validatorsResponse?.validators;

        return validators.map((v) => v.operator_address);
    } catch (error) {
        console.error(`Failed to fetch validators: ${error}`);
        return [];
    }
}

/**
 * Main function to fetch delegators and write them to a CSV file.
 */
async function run() {
  let activeDelegators = {};
  let inactiveDelegators = {};

  try {
    const v_addresses = await fetchValidators();
    for (const v_addr of v_addresses) {
      const { stdout, stderr } = await exec(`dymd query staking validator ${v_addr} -o json`);
      if (stderr) {
        throw new Error(stderr);
      }

      const validatorDetails = JSON.parse(stdout);
      const status = validatorDetails?.status;

      // Determine active or inactive based on status
      const delegators = status === 'BOND_STATUS_BONDED' ? activeDelegators : inactiveDelegators;

      await fetchDelegators(v_addr, delegators);
    }

    // Write active validators to file
    const activeCsvString = generateCsvString(activeDelegators);
    const activeFilename = generateFilename('gatorhead_active_validators');
    fs.writeFile(activeFilename, activeCsvString, handleFileWriteError);

    // Write inactive validators to file
    const inactiveCsvString = generateCsvString(inactiveDelegators);
    const inactiveFilename = generateFilename('gatorhead_inactive_validators');
    fs.writeFile(inactiveFilename, inactiveCsvString, handleFileWriteError);
  } catch (error) {
    console.error(`An error occurred during execution: ${error}`);
  }
}

function generateCsvString(delegators) {
  let csvString = '';
  for (const delgator_dym_addr in delegators) {
    const hex_addr = convertToHex(delgator_dym_addr);
    if (!hex_addr) continue;
    const staked = delegators[delgator_dym_addr];
    csvString += `${hex_addr.toLowerCase()},${staked};\n`;
  }
  return csvString;
}

function handleFileWriteError(err) {
  if (err) {
    console.error('Error writing CSV file:', err);
    return;
  }
  console.log('CSV file written successfully');
}

function generateFilename(type) {
  const date = new Date();
  const dateString = `${date.getFullYear()}${("0" + (date.getMonth() + 1)).slice(-2)}${("0" + date.getDate()).slice(-2)}`;
  return `${type}_${dateString}.csv`;
}

run();