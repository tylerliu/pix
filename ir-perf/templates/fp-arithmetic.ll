; Declare an external "sink" so the compiler can't optimize away your result.
declare void @sink(i64)

define void @bench_loop(i64 %N) {
entry:
  %cmp = icmp sgt i64 %N, 0
  br label %loop

loop:
  %i = phi i64 [ 0, %entry ], [ %next_i, %loop ]
  %acc = phi double [ 1.0, %entry ], [ %next_acc, %loop ]
  
  ; --- The instruction you want to measure: ---
  %next_acc = fadd double %acc, 1.0
  ; -------------------------------------------
  
  %next_i = add i64 %i, 1
  %done = icmp eq i64 %next_i, %N
  br i1 %done, label %exit, label %loop

exit:
  %op1 = fptosi double %acc to i64
  call void @sink(i64 %op1)
  ret void
}