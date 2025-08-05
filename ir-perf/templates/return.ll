; Adjust the DataLayout and Triple for your target, or let llc infer them.
; (You can `llc -march=... -o-` to see the defaults.)

; Declare an external "sink" so the compiler can't optimize away your result.
declare void @sink(i64)

define i64 @bench_function(i64 %N) {
entry:
  ; --- The return instructions you want to measure: ---
  ; Return pattern will be inserted here
  ; -------------------------------------------
} 