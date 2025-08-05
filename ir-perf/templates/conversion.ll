define void @bench_loop(i64 %N) {
entry:
  %cmp = icmp sgt i64 %N, 0
  %ptr = getelementptr inbounds [4 x i8], [4 x i8]* @.str, i32 0, i32 0
  %acc = fadd double 3.5, 0.834723
  %op = add i32 42, 348
  %acc2 = fadd float 1.5, 4.0
  br label %loop

loop:
  %i = phi i64 [ 0, %entry ], [ %next_i, %loop ]
  %sum = phi i64 [ 0, %entry ], [ %next_sum, %loop ]
  
  ; --- The instruction you want to measure: ---
  %next_sum = fadd double %acc, 1.0
  ; -------------------------------------------
  
  %next_i = add i64 %i, 1
  %done = icmp eq i64 %next_i, %N
  br     i1 %done, label %loop, label %exit

exit:
  ; Use the result from the loop to prevent optimization
  call void @sink(i64 %sum)
  ret void
}

@.str = private unnamed_addr constant [4 x i8] c"abc\00", align 1

declare void @sink(i64) 