from ..lib.cpuifs.axi4lite import FlatAXI4Lite
from ..lib.sim_testcase import SimTestCase


class TestEvenWrPath(SimTestCase):
    cpuif = FlatAXI4Lite()
    wr_path_parity = True
    extra_tb_files = [
        "../lib/external_reg.sv",
    ]
    init_hwif_in = False
    clocking_hwif_in = False

    def test_dut(self):
        self.run_test()


class TestOddWrPath(TestEvenWrPath):
    odd_parity = True


class TestOddWrPathBytewise(TestOddWrPath):
    # Both parity features together, as the SMC FuSa regblocks are generated
    bytewise_parity = True
