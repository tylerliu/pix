; Adjust the DataLayout and Triple for your target, or let llc infer them.
; (You can `llc -march=... -o-` to see the defaults.)

; Declare an external "sink" so the compiler can't optimize away your result.
declare void @sink(i64)

define i64 @iteration(i64 %op1) {
  ; --- The instruction you want to measure: ---
  ; Alloca pattern will be inserted here
  ; -------------------------------------------

  ret i64 %next_op1
}

define void @dummy() {
  ret void
}

define void @bench_loop(i64 %N) {
entry:
  br label %loop

loop:
  %iv    = phi i64 [0, %entry], [%next_iv, %loop]
  %op   = phi i64 [0, %entry], [%next_op, %loop]

  %next_op = call i64 @iteration(i64 %op)

  ; increment loop counter
  %next_iv   = add  i64 %iv, 1
  %cmp   = icmp slt  i64 %iv, %N
  br     i1 %cmp, label %loop, label %exit

exit:
  call void @sink(i64 %op)    ; prevent dead-code elimination
  ret void
} 