; Adjust the DataLayout and Triple for your target, or let llc infer them.
; (You can `llc -march=... -o-` to see the defaults.)

; Declare an external "sink" so the compiler can't optimize away your result.
declare void @sink(i64)

define void @bench_loop(i64 %N) {
entry:
  br label %loop

loop:
  %iv    = phi i64 [0, %entry], [%next_iv, %loop]
  %op1   = phi i64 [1, %entry], [%next_op1, %loop]

  ; --- The instruction you want to measure: ---
  %next_op1 = add i64 %op1, 1
  ; -------------------------------------------

  ; increment loop counter
  %next_iv   = add  i64 %iv, 1
  %cmp   = icmp slt  i64 %iv, %N
  br     i1 %cmp, label %loop, label %exit

exit:
  call void @sink(i64 %op1)    ; prevent dead-code elimination
  ret void
} 