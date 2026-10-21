from typing import TYPE_CHECKING, List
import inspect
import os

import jinja2 as jj

from ..utils import clog2, is_pow2, roundup_pow2

if TYPE_CHECKING:
    from ..exporter import RegblockExporter

class CpuifBase:

    # Path is relative to the location of the class that assigns this variable
    template_path = ""

    # Whether this interface can expose the write parity sideband that
    # --parity-wr-path requires (cpuif_wr_datachk / cpuif_wr_strbchk)
    supports_wr_path_parity = False

    def __init__(self, exp:'RegblockExporter'):
        self.exp = exp
        self.reset = exp.ds.top_node.cpuif_reset

    @property
    def addr_width(self) -> int:
        return self.exp.ds.addr_width

    @property
    def data_width(self) -> int:
        return self.exp.ds.cpuif_data_width

    @property
    def data_width_bytes(self) -> int:
        return self.data_width // 8

    @property
    def wr_datachk_width(self) -> int:
        # One parity bit per write-data byte (AXI5 WDATACHK)
        return self.data_width_bytes

    @property
    def wr_strbchk_width(self) -> int:
        # One parity bit per 8 write strobes (AXI5 WSTRBCHK)
        return (self.data_width_bytes + 7) // 8

    @property
    def port_declaration(self) -> str:
        raise NotImplementedError()

    @property
    def parameters(self) -> List[str]:
        """
        Optional list of additional parameter declarations this CPU interface
        provides to the module's definition
        """
        return []

    def _get_template_path_class_dir(self) -> str:
        """
        Traverse up the MRO and find the first class that explicitly assigns
        template_path. Returns the directory that contains the class definition.
        """
        for cls in inspect.getmro(self.__class__):
            if "template_path" in cls.__dict__:
                class_dir = os.path.dirname(inspect.getfile(cls))
                return class_dir
        raise RuntimeError


    def get_implementation(self) -> str:
        class_dir = self._get_template_path_class_dir()
        loader = jj.FileSystemLoader(class_dir)
        jj_env = jj.Environment(
            loader=loader,
            undefined=jj.StrictUndefined,
        )

        context = {
            "cpuif": self,
            "get_always_ff_event": self.exp.dereferencer.get_always_ff_event,
            "get_resetsignal": self.exp.dereferencer.get_resetsignal,
            "clog2": clog2,
            "is_pow2": is_pow2,
            "roundup_pow2": roundup_pow2,
            "ds": self.exp.ds,
        }

        template = jj_env.get_template(self.template_path)
        return template.render(context)
