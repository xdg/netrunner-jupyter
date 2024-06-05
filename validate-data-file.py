#!/usr/bin/env python
import warnings
warnings.simplefilter(action="ignore", category=FutureWarning)

import epiphany as ep
import sys

file=sys.argv[1]
print(f"\nValidating {file}")
id_df = ep.get_id_data_from_file("data/cards/cards.json")
ep.validate_file(file, id_df)
