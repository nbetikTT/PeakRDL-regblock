from ..lib.cpuifs.axi4lite import FlatAXI4Lite
from ..lib.sim_testcase import SimTestCase


class TestEvenParityExport(SimTestCase):
    cpuif = FlatAXI4Lite()
    bytewise_parity = True
    parity_export = True

    def test_dut(self):
        self.run_test()


class TestOddParityExport(TestEvenParityExport):
    odd_parity = True
