{% extends "lib/tb_base.sv" %}
{%- set P = "~" if testcase.odd_parity else "" %}

{% block declarations %}
    logic [3:0] s_axil_wdatachk;
    logic [0:0] s_axil_wstrbchk;
    logic       wr_path_parity_error;
    logic [3:0] corrupt_datachk = '0;
    logic       corrupt_strbchk = '0;
    int         error_cycles = 0;
    logic [31:0] rd;
{%- if testcase.bytewise_parity %}
    logic [regblock_pkg::N_PARITY_FIELDS-1:0] field_parity_error;
    logic [$clog2(regblock_pkg::N_PARITY_BITS)-1:0] parity_inject_sel = '0;
    logic parity_inject_strobe = '0;
{%- endif %}
{% endblock %}

{% block clocking_dirs %}
        input  wr_path_parity_error;
        output corrupt_datachk;
        output corrupt_strbchk;
{% endblock %}

{% block dut_support %}
    {% sv_line_anchor %}
    // Sideband generated the way an AXI5 manager would, with optional corruption
    always_comb begin
        for (int b = 0; b < 4; b++) begin
            s_axil_wdatachk[b] = ({{P}}^s_axil_wdata[b*8 +: 8]) ^ corrupt_datachk[b];
        end
        s_axil_wstrbchk = ({{P}}^s_axil_wstrb) ^ corrupt_strbchk;
    end

    always @(posedge clk) if (!rst && wr_path_parity_error) error_cycles++;

    external_reg ext_reg_inst (
        .clk(clk),
        .rst(rst),
        .req(hwif_out.ext.req),
        .req_is_wr(hwif_out.ext.req_is_wr),
        .wr_data(hwif_out.ext.wr_data),
        .wr_biten(hwif_out.ext.wr_biten),
        .rd_ack(hwif_in.ext.rd_ack),
        .rd_data(hwif_in.ext.rd_data),
        .wr_ack(hwif_in.ext.wr_ack)
    );

    // The external register must receive the parity that arrived with the write,
    // corruption included, so its consumer can check at the point of use
    always @(posedge clk) begin
        if (!rst && hwif_out.ext.req && hwif_out.ext.req_is_wr) begin
            for (int b = 0; b < 4; b++) begin
                assert(hwif_out.ext.wr_datachk[b] == (({{P}}^hwif_out.ext.wr_data[b*8 +: 8]) ^ corrupt_datachk[b]))
                    else $error("ext.wr_datachk[%0d] does not match the received parity", b);
            end
        end
    end
{% endblock %}

{% block seq %}
    {% sv_line_anchor %}
    ##1;
    cb.rst <= '0;
    ##2;

    // 1) Clean writes to internal, sparse and external registers never flag
    cpuif.write('h0, 32'hA5C3_0F11);
    cpuif.write('h4, 32'h00BB_00AA);
    cpuif.write('h8, 32'h1234_5678);
    ##3;
    assert(error_cycles == 0) else $error("Clean writes flagged %0d cycles", error_cycles);
    cpuif.read('h0, rd);
    assert(rd == 32'hA5C3_0F11) else $error("Readback 0x0 = %h", rd);
    cpuif.read('h4, rd);
    assert(rd == 32'h00BB_00AA) else $error("Readback 0x4 = %h", rd);
    cpuif.read('h8, rd);
    assert(rd == 32'h1234_5678) else $error("Readback 0x8 = %h", rd);

    // 2) Corrupt parity on a strobed byte flags while the write is consumed, then stops
    error_cycles = 0;
    cb.corrupt_datachk <= 4'b0001;
    @cb;
    cpuif.write('h0, 32'h0000_00FF);
    ##3;
    assert(error_cycles >= 1) else $error("Corrupt strobed byte parity was not flagged");
    begin
        automatic int n = error_cycles;
        ##5;
        assert(error_cycles == n) else $error("Checker kept flagging after the write ended");
    end

    // 3) Corrupt parity on an unstrobed byte is masked by the strobe
    error_cycles = 0;
    cb.corrupt_datachk <= 4'b1000;
    @cb;
    cpuif.write('h0, 32'h1122_3344, 4'b0111);
    ##3;
    assert(error_cycles == 0) else $error("Unstrobed byte parity was flagged %0d cycles", error_cycles);
    cpuif.read('h0, rd);
    assert(rd == 32'h0022_3344) else $error("Readback after partial write = %h", rd);

    // 4) Corrupt strobe parity flags
    error_cycles = 0;
    cb.corrupt_datachk <= '0;
    cb.corrupt_strbchk <= 1'b1;
    @cb;
    cpuif.write('h4, 32'h0);
    ##3;
    assert(error_cycles >= 1) else $error("Corrupt strobe parity was not flagged");

    // 5) Corruption while idle, and during reads, never flags
    error_cycles = 0;
    cb.corrupt_strbchk <= 1'b0;
    cb.corrupt_datachk <= '1;
    @cb;
    ##5;
    cpuif.read('h4, rd);
    ##3;
    assert(error_cycles == 0) else $error("Idle/read corruption flagged %0d cycles", error_cycles);

    // 6) External register write with corrupt parity flags and forwards the received parity
    error_cycles = 0;
    cb.corrupt_datachk <= 4'b0010;
    @cb;
    cpuif.write('h8, 32'hDEAD_BEEF);
    ##3;
    assert(error_cycles >= 1) else $error("Corrupt parity on external write was not flagged");
    cb.corrupt_datachk <= '0;
    @cb;
{%- if testcase.bytewise_parity %}

    // 7) Write-path errors do not disturb the stored-field parity
    assert(field_parity_error == '0) else $error("field_parity_error = %h after write-path tests", field_parity_error);
{%- endif %}
{% endblock %}
