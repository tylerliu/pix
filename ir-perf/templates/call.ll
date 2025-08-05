; Adjust the DataLayout and Triple for your target, or let llc infer them.
; (You can `llc -march=... -o-` to see the defaults.)

; Declare an external "sink" so the compiler can't optimize away your result.
declare void @sink(i64)

; Helper functions for call benchmarks
define void @helper_void() {
  ret void
}

define i64 @helper_1arg(i64 %x) {
  ret i64 %x
}

define i64 @helper_2args(i64 %x, i64 %y) {
  %sum = add i64 %x, %y
  ret i64 %sum
}

define i64 @helper_4args(i64 %x, i64 %y, i64 %z, i64 %w) {
  %sum1 = add i64 %x, %y
  %sum2 = add i64 %z, %w
  %result = add i64 %sum1, %sum2
  ret i64 %result
}

; Function pointer for indirect calls
@function_ptr = global i64 (i64)* @helper_1arg
@function_array = global [4 x i64 (i64)*] [i64 (i64)* @helper_1arg, i64 (i64)* @helper_1arg, i64 (i64)* @helper_1arg, i64 (i64)* @helper_1arg]

define void @bench_loop(i64 %N) {
entry:
  br label %loop

loop:
  %iv    = phi i64 [0, %entry], [%next_iv, %loop]
  %op1   = phi i64 [0, %entry], [%next_op1, %loop]

  ; --- The instruction you want to measure: ---
  ; Call pattern will be inserted here
  ; -------------------------------------------

  ; increment loop counter
  %next_iv   = add  i64 %iv, 1
  %cmp   = icmp slt  i64 %iv, %N
  br     i1 %cmp, label %loop, label %exit

exit:
  call void @sink(i64 %op1)    ; prevent dead-code elimination
  ret void
} 