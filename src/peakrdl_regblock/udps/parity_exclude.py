from typing import Any

from systemrdl.component import Field, Reg
from systemrdl.node import Node
from systemrdl.udp import UDPDefinition


class ParityExclude(UDPDefinition):
    """
    When set true on a Reg or Field, the bytewise parity flow (--parity-byte)
    skips this node — no parity storage, no mismatch logic, no slot in the
    field_parity_error vector or parity_inject_sel decoder.

    A Reg-level setting applies to every field in the reg. A Field-level
    setting overrides only that field. Has no effect under legacy paritycheck.
    """
    name = "parity_exclude"
    valid_components = {Field, Reg}
    valid_type = bool
    default_assignment = True

    def get_unassigned_default(self, node: "Node") -> Any:
        return False
