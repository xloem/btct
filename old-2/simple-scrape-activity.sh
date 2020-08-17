#!/bin/bash
bcli=${HOME}/pkg/bitcoin-0.18.0/bin/bitcoin-cli
$bcli getblockhash 100000 > blockhash.txt
while true
do
	$bcli getblock $(<blockhash.txt) > block.txt
	echo $(sed -ne 's/.*mediantime.* \(.*\),/\1/p' < block.txt) $(grep '    ' < block.txt | wc -l)
	sed -ne 's/.*nextblockhash.* "\(.*\)"/\1/p' < block.txt > blockhash.txt || break
done
