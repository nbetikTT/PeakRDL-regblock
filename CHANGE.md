# Changes

## Parity protection
- Added `--odd-parity` flag: emit odd parity instead of even.
- Added `--parity-byte` flag: byte-wise per-field parity storage with continuous comparator,
  per-field sticky error vector output, transient single-bit injection port for self-test,
  and a shared `error_clear_i` input to clear all sticky error bits.
- Existing `paritycheck` RDL property continues to work unchanged when `--parity-byte` is not set.
- Added `--parity-wr-path` flag (flattened AXI4-Lite only): adds AXI5-style `s_axil_wdatachk` /
  `s_axil_wstrbchk` inputs, carries the received write parity alongside the registered write data
  into the decode stage, and recomputes-and-compares it against the write data and byte-enables
  for strobed bytes while a write is consumed. Mismatches drive the combinational
  `wr_path_parity_error` output. External registers gain `hwif_out.<reg>.wr_datachk` (per-byte
  parity of `wr_data`); external blocks gain `wr_datachk` and `wr_strbchk`. Polarity follows
  `--odd-parity`.
- Added `--parity-export` flag (requires `--parity-byte`): every parity-protected field with a
  value output also gets `hwif_out.<field>.parity`, the stored per-byte parity of `value`, so a
  consumer can re-check the value at its point of use instead of trusting the wire.
