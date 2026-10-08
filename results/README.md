# Results

New runs use `results/<UTC timestamp>-<unique suffix>/`. Each directory contains report(s) and a manifest with resolved inputs, source hashes, code state, and dependency versions. Generated run directories are ignored by Git unless deliberately added.

`history/root/` and `history/dummy_data/` preserve all previous saved outputs byte-for-byte, separated by original location. Their filenames and embedded scenarios retain distinctions among old objectives, bonus policies, type caps, height caps, and profitability experiments. Their input provenance is incomplete; they are historical evidence, not automatically current results.

`history/index.json` records original paths, archived paths, and SHA-256 hashes. Importing these files did not regenerate their values or infer missing original run metadata.
