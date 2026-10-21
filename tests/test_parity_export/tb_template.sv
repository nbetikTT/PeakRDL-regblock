{% extends "lib/tb_base.sv" %}
{%- set P = "~" if testcase.odd_parity else "" %}

{% block declarations %}
    logic [regblock_pkg::N_PARITY_FIELDS-1:0] field_parity_error;
    logic [$clog2(regblock_pkg::N_PARITY_BITS)-1:0] parity_inject_sel = '0;
    logic parity_inject_strobe = '0;
    logic [31:0] rd;
{% endblock %}

{% block dut_support %}
    {% sv_line_anchor %}
    // The exported parity is the stored parity of the value it travels with,
    // every cycle, also for a partial top byte
    always @(posedge clk) begin
        if (!rst) begin
            for (int b = 0; b < 4; b++) begin
                assert(hwif_out.full.f.parity[b] == ({{P}}^hwif_out.full.f.value[b*8 +: 8]))
                    else $error("full.f.parity[%0d] does not match value", b);
            end
            assert(hwif_out.narrow.f.parity[0] == ({{P}}^hwif_out.narrow.f.value[7:0]))
                else $error("narrow.f.parity[0] does not match value");
            assert(hwif_out.narrow.f.parity[1] == ({{P}}^hwif_out.narrow.f.value[12:8]))
                else $error("narrow.f.parity[1] does not match value");
        end
    end
{% endblock %}

{% block seq %}
    {% sv_line_anchor %}
    ##1;
    cb.rst <= '0;
    ##2;

    cpuif.write('h0, 32'hA5C3_0F11);
    cpuif.write('h4, 32'h0015_1F3C);
    ##2;
    cpuif.read('h0, rd);
    assert(rd == 32'hA5C3_0F11) else $error("Readback 0x0 = %h", rd);
    cpuif.read('h4, rd);
    assert(rd == 32'h0015_1F3C) else $error("Readback 0x4 = %h", rd);
    assert(field_parity_error == '0) else $error("Unexpected field parity error %b", field_parity_error);

    cpuif.write('h0, 32'h0000_0000);
    cpuif.write('h0, 32'hFFFF_FFFF);
    cpuif.write('h4, 32'h0000_1000);
    ##2;
{% endblock %}
