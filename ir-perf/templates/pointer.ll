; Adjust the DataLayout and Triple for your target, or let llc infer them.
; (You can `llc -march=... -o-` to see the defaults.)

; Declare an external "sink" so the compiler can't optimize away your result.
declare void @sink(i64)

%struct.MyStruct = type { i32, i64, double }

define void @bench_loop(i64 %N) {
entry:
  %base_ptr = alloca [10 x i64]
  %vec = alloca <4 x i32>
  %agg = alloca %struct.MyStruct
  
  ; Load values outside the loop
  %vec_val = load <4 x i32>, <4 x i32>* %vec
  %agg_val = load %struct.MyStruct, %struct.MyStruct* %agg
  
  br label %loop

loop:
  %iv    = phi i64 [0, %entry], [%next_iv, %loop]

  ; --- The instruction you want to measure: ---
  %ptr = getelementptr [10 x i64], [10 x i64]* %base_ptr, i64 0, i64 %iv
  %next_sum = add i64 %sum, 1
  ; -------------------------------------------

  ; increment loop counter
  %next_iv   = add  i64 %iv, 1
  %cmp   = icmp slt  i64 %iv, %N
  br     i1 %cmp, label %loop, label %exit

exit:
  call void @sink(i64 %iv)    ; prevent dead-code elimination
  ret void
} 