# A4-1S internal allocation-item binary schema

This note freezes the internal binary interchange used to launch one native
allocation decision per child process.  It is synthetic-only infrastructure,
not a public command, a scientific result, or authorization to run the cost
panel.  The hidden command is:

```text
a4_1s_native allocation-item INPUT OUTPUT
```

The command requires exactly those two paths.  It does not appear in the
user-facing usage string.  A request contains either one product arm or one
global allocation; no process may contain multiple decisions.

## Primitive encodings

There is no alignment or implicit padding.  Fields occur in the exact order
listed below.

| Type | Encoding |
|---|---|
| `u8` | one unsigned byte |
| `u32` | four-byte unsigned integer, little-endian |
| `i32` | two's-complement 32-bit integer, little-endian |
| `u64` | eight-byte unsigned integer, little-endian |
| `bool8` | `u8`, canonical values restricted to `0` and `1` |
| `magic[8]` | the eight literal ASCII bytes shown |

An exact squared-error objective is encoded as:

```text
i32 binary_grid_exponent       # exactly -298
u32 numerator_byte_count       # positive
byte[numerator_byte_count]     # shortest unsigned ASCII decimal; zero is "0"
u32 denominator_byte_count     # positive
byte[denominator_byte_count]   # shortest positive ASCII decimal
```

The numerator and denominator must already be coprime, the numerator must be
nonnegative, and the denominator must be positive.  Leading zeros are
forbidden except for the one-byte numerator `"0"`.

An exact curve body has one record for each implicit requested cardinality
`K=1..maximum_cardinality`, in increasing order:

```text
u32 effective_cardinality      # min(K,H), in [1,K]
exact_objective exact_sse
```

The decoder requires nonincreasing exact SSE, `effective_cardinality=min(K,H)`,
and an identical objective throughout the unreachable nominal tail `K>H`.

## Canonical item identifiers

Product item ids are not opaque.  They uniquely cover 256 decisions in
arbitrary-before-dyadic order:

```text
rate_index = 0 for capacity 16 (B4), 1 for capacity 256 (B8)
group_id = first_curve_id / 2, in 0..63
cardinality_set = 0 for arbitrary, 1 for dyadic
item_id = ((rate_index * 64 + group_id) * 2) + cardinality_set
```

The product curve ids must be exactly `(2*group_id, 2*group_id+1)`, in that
order.  Thus ids `0..127` are B4 product items and `128..255` are B8 product
items.  Global id `256` is B4 with budget 256; global id `257` is B8 with
budget 512.  Any inconsistent descriptor is rejected before allocation.

## Input: `A4ALI001`

Every request begins with:

```text
magic[8] "A4ALI001"
u32 schema_version             # exactly 1
u32 item_kind                  # 1 product, 2 global
u32 item_id                    # mapping above
```

### Product request (`item_kind=1`)

```text
u32 capacity                   # exactly 16 or 256
u32 cardinality_set            # 0 arbitrary, 1 dyadic
u32 curve_count                # exactly 2
u32 maximum_cardinality        # exactly capacity

u32 first_curve_id
exact_curve_body first_curve   # K=1..capacity
u32 second_curve_id
exact_curve_body second_curve  # K=1..capacity

magic[8] "A4AIEND1"
EOF
```

### Global request (`item_kind=2`)

```text
u32 bit_budget                 # 256 for id 256; 512 for id 257
u32 curve_count                # exactly 128
u32 maximum_cardinality        # exactly 256

repeat coordinate=0..127:
  u32 curve_id                 # exactly coordinate
  exact_curve_body curve       # K=1..256

magic[8] "A4AIEND1"
EOF
```

The terminal is mandatory, and even one trailing byte after it is invalid.

## Output: `A4ALO001`

Every successful result begins with:

```text
magic[8] "A4ALO001"
u32 schema_version             # exactly 1
u32 item_kind                  # echoes the validated input kind
u32 item_id                    # echoes the validated canonical id
```

### Product result (`item_kind=1`)

```text
u32 capacity
u32 cardinality_set
u32 curve_count                # exactly 2

u32 first_curve_id
u32 first_requested_cardinality
u32 first_effective_cardinality
bool8 first_nominal_alphabet_reachable

u32 second_curve_id
u32 second_requested_cardinality
u32 second_effective_cardinality
bool8 second_nominal_alphabet_reachable

u64 used_states                # requested K1*K2, <= capacity
bool8 all_nominal_alphabets_reachable
exact_objective selected_sse
u64 optimized_candidate_evaluation_count

magic[8] "A4AOEND1"
EOF
```

The aggregate reachability bit must be the conjunction of the two per-curve
bits.  Candidate evaluation counts are exactly `capacity` for arbitrary
allocation and `log2(capacity)+1` for dyadic allocation: respectively 16/256
and 5/9 for B4/B8.  This is actual optimized-search work, not the exhaustive
valid-tuple count.

### Global result (`item_kind=2`)

```text
u32 bit_budget
u32 curve_count                # exactly 128
u32 used_bits                  # sum of selected widths, <= budget
bool8 all_nominal_alphabets_reachable
exact_objective selected_sse
u64 transition_evaluation_count
u32 selected_record_count      # exactly 128

repeat coordinate=0..127:
  u32 curve_id                 # exactly coordinate
  u8 selected_bit_width        # in 0..8
  u32 requested_cardinality    # exactly 2^selected_bit_width
  u32 effective_cardinality
  bool8 nominal_alphabet_reachable

magic[8] "A4AOEND1"
EOF
```

The aggregate reachability bit is the conjunction of all 128 coordinate bits.
The transition diagnostic counts every exact objective transition actually
evaluated by the frozen DP:

```text
sum over coordinate c=0..127
  sum over used=0..min(8*c, bit_budget)
    (min(8, bit_budget-used) + 1)
```

It is exactly `254592` for budget 256 and `438912` for budget 512.

## Failure and completeness rules

Malformed magic, version, id mapping, field range, rational, curve invariant,
terminal, or EOF makes the native process exit with the existing
`A4-1S IMPLEMENTATION_INVALID` path and no valid result.  The output file is
opened only after the complete request has been validated and the allocation
plus its diagnostics have been replay-checked.  A consumer must parse every
field, require the output terminal, and require exact EOF; file existence or a
zero child exit status alone is insufficient.

The implementation is header-only in `research/a4_1s/allocation_curve_io.hpp`
and `research/a4_1s/allocation_item_cli*.hpp`, included by the existing native
entry translation unit.  It deliberately adds no compiled translation unit:
the frozen `compile_commands.json` inventory remains exactly seven C++ source
files.
