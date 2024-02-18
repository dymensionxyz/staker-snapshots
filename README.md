# Dymension staker snapshots

This repo contains historical snapshots of Dymension stakers. These snapshots are provided by Dymension validators. Snapshots follow the following format in CSV: 

File name: `validator_YYYYMMDD.csv: staked DYM and its owners`

```csv
delagatoraddress, delegated dym;
delagatoraddress, delegated dym;
...
delagatoraddress, delegated dym;
```

* be aware that this is not sybil resistant: an individual can spin up multiple wallets and show up as multiple holders.
