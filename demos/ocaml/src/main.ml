
open Printf;;

open Somemodule;;

let rec fib n =
	if n < 1 then 1
	else if n == 1 then 1
	else fib(n-1) + fib(n-2);;

for i=0 to 10 do
	Somemodule.pprint "next";
	Printf.printf " %d %d\n" i (fib i)
done;;

print_newline();;

