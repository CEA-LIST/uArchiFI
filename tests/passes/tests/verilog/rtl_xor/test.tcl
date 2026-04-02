if {[info exists ::env(YOSYS_VARIANT)]} {
    set variant $::env(YOSYS_VARIANT)
} else {
    set variant "0.61"
}

puts "Running with YOSYS_VARIANT=$variant"

if {$variant == "0.25"} {
    puts "Fault_rtlil already loaded"
} elseif {$variant == "0.61"} {
    yosys plugin -i fault_rtlil
}

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

yosys select a:fault=1 w:\$flatten* %d

select n:*a n:*b

if {$variant == "0.25"} {
    fault_rtlil -cnt 1 -timing 1
} elseif {$variant == "0.61"} {
    fault_rtlil -cnt 1 -timing 1 -effect xor
}

write_rtlil result.rtlil

select -clear
show -prefix ./result -format svg -width
async2sync
dffunmap

write_smt2 -wires ./result.smt2
