yosys plugin -i fault_rtlil

yosys -import

read_verilog ./addr.v ./tb_addr.v 

prep -top tb_addr

uniquify; hierarchy -top tb_addr

async2sync

delete -input; setundef -undriven -zero

select -clear;

select tb_addr.dut/a tb_addr.dut/b

setattr -set fault 1

yosys cd;

yosys flatten

select n:*a

fault_rtlil -cnt 50 -timing 1:2 -width 4 -bypass

write_rtlil result.rtlil

select -clear
show -prefix ./result -format svg -width
async2sync
dffunmap

write_smt2 -wires ./result.smt2
