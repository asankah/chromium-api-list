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

If `--commit` is specified, then the updated list of APIs is committed to the
repository. The commit message, where possible, will identify the commit hash in
the Chromium repository or the `Cr-Commit-Position`.

Description of columns:

| Column           | Description                                                |
| ---------------- | ---------------------------------------------------------- |
| `interface`      | Name of the interface.                                     |
| `name`           | Name of member. For a row describing an interface, the name field is empty. |
| `entity_type`   | One of `interface`, `operation`, `attribute`, `constant`   |
| `idl_type`       | The IDL data type of the member. Empty for interfaces.     |
| `syntactic_form` | Human readable version of `idl_type`. Useful for display, but should not be used for anything else. |
| `use_counter`    | Chromium UseCounter id for the member. Only present for attributes, interfaces, and operations whose prevalence is being measured.  Results of this measurement can be seen in the [Chrome Platform Status][CS] page. |
| `secure_context` | `True` or `False` indicating whether the API requires a secure context. |
| `high_entropy`   | `True` or `False` indicating whether this API is known to or suspected of being highly identifying. |

[CS]: https://www.chromestatus.com/metrics/feature/popularity
