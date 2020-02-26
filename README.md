# Chromium API List

This repository contains a single file that will contain the list of Blink APIs
that are shipped with Chromium. The list should be updated roughly every day.

The goal here is to track changes to the APIs over time. There will be some
schema changes that happen along the way, and that will affect whether a simple
'diff' is sufficient to tell what changed between two snapshots.

To build the API list, start with a [Chromium checkout][CrCode] and build the
`generate_high_entropy_list` target. E.g.:

```sh
autoninja -C out/Debug generate_high_entropy_list
```

The list is written to a file named `high_entropy_list.csv` in `out/Debug`
or whatever your output directory is.

[CrCode]: https://www.chromium.org/developers/how-tos/get-the-code

