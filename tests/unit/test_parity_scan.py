"""Unit tests for the bytewise-parity scanner population in DesignState."""
import os
from systemrdl import RDLCompiler
from systemrdl.messages import MessagePrinter, Severity
from peakrdl_regblock import RegblockExporter
from peakrdl_regblock.udps import ALL_UDPS


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class _CountingPrinter(MessagePrinter):
    """MessagePrinter that records messages by severity for assertion in tests."""
    def __init__(self):
        super().__init__()
        self.warnings = []  # list of message strings
        self.errors = []

    def emit_message(self, lines):
        # Don't actually print to stderr — keep test output clean.
        pass

    def print_message(self, severity, text, src_ref):
        if severity == Severity.WARNING:
            self.warnings.append(text)
        elif severity in (Severity.ERROR, Severity.FATAL):
            self.errors.append(text)
        # swallow output


def _elaborate(rdl_relpath: str, message_printer=None):
    if message_printer is not None:
        rdlc = RDLCompiler(message_printer=message_printer)
    else:
        rdlc = RDLCompiler()
    for udp in ALL_UDPS:
        rdlc.register_udp(udp)
    rdlc.compile_file(os.path.join(REPO_ROOT, "hdl-src/regblock_udps.rdl"))
    rdlc.compile_file(os.path.join(REPO_ROOT, rdl_relpath))
    return rdlc.elaborate()


def test_bytewise_off_leaves_collections_empty(tmp_path):
    root = _elaborate("tests/test_parity/regblock.rdl")
    e = RegblockExporter()
    e.export(root, str(tmp_path), module_name="regblock", package_name="regblock_pkg")
    assert e.ds.bytewise_parity is False
    assert e.ds.has_bytewise_parity is False
    assert e.ds.parity_fields == []
    assert e.ds.parity_bits == []


def test_bytewise_on_collects_all_storage_fields(tmp_path):
    # test_parity/regblock.rdl has fields: f1[16], f2[8], f3[1] in 1 + 8 = 9 reg instances.
    root = _elaborate("tests/test_parity/regblock.rdl")
    e = RegblockExporter()
    e.export(
        root, str(tmp_path),
        module_name="regblock", package_name="regblock_pkg",
        bytewise_parity=True,
    )
    assert e.ds.has_bytewise_parity is True
    # 3 fields per reg instance, 9 reg instances total = 27 fields
    assert len(e.ds.parity_fields) == 27

    # f1 is 16 bits = 2 parity bytes; f2 is 8 bits = 1; f3 is 1 bit = 1.
    # Per reg: 2 + 1 + 1 = 4 parity bits. 9 regs = 36 parity bits.
    assert len(e.ds.parity_bits) == 36


def test_bytewise_byte_count_for_widths(tmp_path):
    """Verify ceil(W/8) byte-count rule for the canonical widths."""
    root = _elaborate("tests/test_parity/regblock.rdl")
    e = RegblockExporter()
    e.export(
        root, str(tmp_path),
        module_name="regblock", package_name="regblock_pkg",
        bytewise_parity=True,
    )

    widths_seen = sorted({node.width for (node, _bc, _f, _p) in e.ds.parity_fields})
    assert widths_seen == [1, 8, 16]

    for (node, byte_count, ferr_idx, first_pinj_idx) in e.ds.parity_fields:
        assert byte_count == (node.width + 7) // 8


def test_paritycheck_with_bytewise_emits_warning(tmp_path):
    """When --parity-byte is on AND a field has paritycheck=true, the scanner
    must warn so users know the property is redundant in this mode."""
    printer = _CountingPrinter()
    # tests/test_parity/regblock.rdl has `default paritycheck;` so every field is tagged.
    root = _elaborate("tests/test_parity/regblock.rdl", message_printer=printer)
    initial = len(printer.warnings)

    e = RegblockExporter()
    e.export(
        root, str(tmp_path),
        module_name="regblock", package_name="regblock_pkg",
        bytewise_parity=True,
    )
    final = len(printer.warnings)
    assert final > initial, (
        "Expected at least one warning when paritycheck and --parity-byte are both on; "
        f"warning count went {initial} -> {final}"
    )
    # Sanity: the new warning text mentions --parity-byte
    new_warnings = printer.warnings[initial:]
    assert any("--parity-byte" in w for w in new_warnings), (
        f"Expected the redundancy warning to mention --parity-byte, got: {new_warnings}"
    )


def test_paritycheck_alone_no_redundancy_warning(tmp_path):
    """Sanity: legacy mode with paritycheck and reset values defined should not
    emit the new redundancy warning."""
    printer = _CountingPrinter()
    root = _elaborate("tests/test_parity/regblock.rdl", message_printer=printer)
    initial = len(printer.warnings)

    e = RegblockExporter()
    e.export(
        root, str(tmp_path),
        module_name="regblock", package_name="regblock_pkg",
        # bytewise_parity defaults to False
    )
    # All fields in the test RDL have explicit reset values, so the legacy
    # "missing reset" warning should not fire either.
    assert len(printer.warnings) == initial, (
        f"Unexpected warnings in legacy mode: "
        f"{initial} -> {len(printer.warnings)}: {printer.warnings[initial:]}"
    )


def test_parity_path_id_format(tmp_path):
    from peakrdl_regblock.parity import parity_path_id

    root = _elaborate("tests/test_parity/regblock.rdl")
    e = RegblockExporter()
    e.export(
        root, str(tmp_path),
        module_name="regblock", package_name="regblock_pkg",
        bytewise_parity=True,
    )

    # The first parity field should be r1.f1 (depth-first ordering).
    first_node, *_ = e.ds.parity_fields[0]
    assert parity_path_id(e.ds.top_node, first_node) == "R1_F1"
    assert parity_path_id(e.ds.top_node, first_node, byte=0) == "R1_F1_BYTE0"
    assert parity_path_id(e.ds.top_node, first_node, byte=1) == "R1_F1_BYTE1"


def test_external_register_is_skipped(tmp_path):
    """An external register's fields must not appear in parity_fields."""
    root = _elaborate("tests/test_parity_bytewise/regblock.rdl")
    e = RegblockExporter()
    e.export(
        root, str(tmp_path),
        module_name="regblock", package_name="regblock_pkg",
        bytewise_parity=True,
    )
    field_names = [node.inst_name for (node, *_) in e.ds.parity_fields]
    assert "f_ext" not in field_names, \
        f"Field 'f_ext' from external reg should be skipped; got {field_names}"


# -----------------------------------------------------------------------------
# parity_exclude UDP
# -----------------------------------------------------------------------------

# Inline RDL exercising every parity_exclude shape: none, reg-level (propagates
# to all child fields), field-level only, and bare `parity_exclude;`. Compiled
# via _elaborate(), which uses register_udp(soft=True) + hdl-src/regblock_udps.rdl
# — the same flow as the peakrdl-cli host. This catches missing RDL declarations
# of the UDP, not just the Python registration.
_PARITY_EXCLUDE_RDL = """
addrmap top {
    default sw=rw; default hw=na;
    reg { field { sw=rw; hw=r; } f_a[8] = 0; } r_normal @ 0x000;
    reg {
        parity_exclude = true;
        field { sw=rw; hw=r; } f_x[8] = 0;
        field { sw=rw; hw=r; } f_y[8] = 0;
    } r_excl_reg @ 0x004;
    reg {
        field { sw=rw; hw=r; } f_in[8] = 0;
        field { sw=rw; hw=r; parity_exclude = true; } f_out[8] = 0;
    } r_mixed @ 0x008;
    reg {
        parity_exclude;
        field { sw=rw; hw=r; } f_z[8] = 0;
    } r_bare @ 0x00C;
};
"""


def _elaborate_inline(rdl_text: str, tmp_path, message_printer=None):
    import os
    if message_printer is not None:
        rdlc = RDLCompiler(message_printer=message_printer)
    else:
        rdlc = RDLCompiler()
    for udp in ALL_UDPS:
        rdlc.register_udp(udp)
    rdlc.compile_file(os.path.join(REPO_ROOT, "hdl-src/regblock_udps.rdl"))
    rdl_path = tmp_path / "inline.rdl"
    rdl_path.write_text(rdl_text)
    rdlc.compile_file(str(rdl_path))
    return rdlc.elaborate()


def test_parity_exclude_udp_is_recognized_in_rdl(tmp_path):
    """Soft-registered UDPs require a matching `property` declaration in
    hdl-src/regblock_udps.rdl. Without it, user RDL fails to parse with
    'Unrecognized property'. This is the regression guard."""
    # Just compiling without raising is the assertion.
    _elaborate_inline(_PARITY_EXCLUDE_RDL, tmp_path)


def test_parity_exclude_skips_excluded_fields(tmp_path):
    root = _elaborate_inline(_PARITY_EXCLUDE_RDL, tmp_path)
    e = RegblockExporter()
    e.export(
        root, str(tmp_path),
        module_name="regblock", package_name="regblock_pkg",
        bytewise_parity=True,
    )
    names = [n.inst_name for (n, *_) in e.ds.parity_fields]
    # f_x, f_y excluded via reg; f_out via field; f_z via bare reg-level.
    assert names == ["f_a", "f_in"], names


def test_parity_exclude_helper_resolves_reg_and_field(tmp_path):
    from peakrdl_regblock.parity import is_parity_excluded
    root = _elaborate_inline(_PARITY_EXCLUDE_RDL, tmp_path)
    top = root.find_by_path("top")

    assert is_parity_excluded(top.find_by_path("r_excl_reg"))
    assert is_parity_excluded(top.find_by_path("r_excl_reg").find_by_path("f_x"))
    assert is_parity_excluded(top.find_by_path("r_excl_reg").find_by_path("f_y"))

    assert not is_parity_excluded(top.find_by_path("r_mixed"))
    assert not is_parity_excluded(top.find_by_path("r_mixed").find_by_path("f_in"))
    assert is_parity_excluded(top.find_by_path("r_mixed").find_by_path("f_out"))

    assert not is_parity_excluded(top.find_by_path("r_normal"))
    assert not is_parity_excluded(top.find_by_path("r_normal").find_by_path("f_a"))


def test_parity_exclude_warns_in_legacy_mode(tmp_path):
    printer = _CountingPrinter()
    root = _elaborate_inline(_PARITY_EXCLUDE_RDL, tmp_path, message_printer=printer)
    initial = len(printer.warnings)
    e = RegblockExporter()
    e.export(
        root, str(tmp_path),
        module_name="regblock", package_name="regblock_pkg",
        # bytewise_parity defaults to False
    )
    new_warnings = printer.warnings[initial:]
    pe_warnings = [w for w in new_warnings if "parity_exclude" in w]
    # r_excl_reg, r_bare (reg-level) and f_out (field-level) — 3 sites.
    assert len(pe_warnings) >= 3, pe_warnings
    assert all("--parity-byte" in w for w in pe_warnings), pe_warnings


def test_parity_exclude_no_warning_under_bytewise(tmp_path):
    printer = _CountingPrinter()
    root = _elaborate_inline(_PARITY_EXCLUDE_RDL, tmp_path, message_printer=printer)
    initial = len(printer.warnings)
    e = RegblockExporter()
    e.export(
        root, str(tmp_path),
        module_name="regblock", package_name="regblock_pkg",
        bytewise_parity=True,
    )
    new_warnings = printer.warnings[initial:]
    pe_warnings = [w for w in new_warnings if "parity_exclude" in w]
    assert pe_warnings == [], pe_warnings
