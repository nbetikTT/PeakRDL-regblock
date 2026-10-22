// External region: {{node.get_path()}}
{% if retime -%}


always_ff {{get_always_ff_event(resetsignal)}} begin
    if({{get_resetsignal(resetsignal)}}) begin
        {{prefix}}.req <= '0;
        {{prefix}}.addr <= '0;
        {{prefix}}.req_is_wr <= '0;
        {{prefix}}.wr_data <= '0;
        {{prefix}}.wr_biten <= '0;
        {%- if wr_path_parity %}
        {{prefix}}.wr_datachk <= '0;
        {{prefix}}.wr_strbchk <= '0;
        {%- endif %}
    end else begin
        {{prefix}}.req <= {{strb}};
        {{prefix}}.addr <= decoded_addr[{{addr_width-1}}:0];
        {{prefix}}.req_is_wr <= decoded_req_is_wr;
        {{prefix}}.wr_data <= decoded_wr_data;
        {{prefix}}.wr_biten <= decoded_wr_biten;
        {%- if wr_path_parity %}
        {{prefix}}.wr_datachk <= decoded_wr_datachk;
        {{prefix}}.wr_strbchk <= decoded_wr_strbchk;
        {%- endif %}
    end
end


{%- else -%}


assign {{prefix}}.req = {{strb}};
assign {{prefix}}.addr = decoded_addr[{{addr_width-1}}:0];
assign {{prefix}}.req_is_wr = decoded_req_is_wr;
assign {{prefix}}.wr_data = decoded_wr_data;
assign {{prefix}}.wr_biten = decoded_wr_biten;
{%- if wr_path_parity %}
assign {{prefix}}.wr_datachk = decoded_wr_datachk;
assign {{prefix}}.wr_strbchk = decoded_wr_strbchk;
{%- endif %}


{%- endif %}
