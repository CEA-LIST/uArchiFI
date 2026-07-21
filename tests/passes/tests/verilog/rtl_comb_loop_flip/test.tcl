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

read_verilog ./comb_loop_split.v

prep -top tricky_example

uniquify; hierarchy -top tricky_example

#yosys select t:\$check
yosys async2sync
#yosys select -clear

#select -module tricky_example:reset*
#delete -input
#setundef -undriven -one
#select -clear
#delete -input; setundef -undriven -zero

#select -clear;

select tricky_example/*

setattr -set fault 1

yosys cd;

yosys flatten

yosys select a:fault=1 w:\$flatten* %d


if {$variant == "0.25"} {
    fault_rtlil -cnt 1 -timing 1
} elseif {$variant == "0.61"} {
    fault_rtlil -cnt 1 -timing 1 -effect flip
}

scc

write_rtlil result.rtlil

select -clear
show -prefix ./result -format svg -width
async2sync
dffunmap

write_smt2 -wires ./result.smt2
